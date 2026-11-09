"""Consultas de solo lectura. Totales SQL independientes de la paginación."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, case, distinct, func

from app import db
from app.models import Asistencia, Membresia, Pago, Plan, Socio
from app.services import METODOS_PAGO
from app.timeutils import ZONA_LA_PAZ

CENTAVOS = Decimal("0.01")
COLUMNAS = {
    "membresias": (
        ("id", "ID"), ("socio", "Socio"), ("plan", "Plan"),
        ("fecha_inicio", "Fecha de inicio"), ("fecha_fin", "Fecha de vencimiento"),
        ("precio_pactado", "Precio pactado"), ("estado", "Estado"),
        ("dias_restantes", "Días restantes"),
    ),
    "pagos": (
        ("id", "ID del pago"), ("fecha_pago", "Fecha del pago (La Paz)"),
        ("socio", "Socio"), ("membresia_id", "Membresía"), ("plan", "Plan"),
        ("monto", "Monto"), ("metodo_pago", "Método"),
        ("referencia", "Referencia"), ("estado", "Estado"),
    ),
    "asistencias": (
        ("id", "ID"), ("socio", "Socio"), ("membresia_id", "Membresía"),
        ("fecha", "Fecha de ingreso"), ("entrada", "Hora de entrada"),
        ("salida", "Fecha y hora de salida"), ("estado", "Estado"),
    ),
}


@dataclass
class Pagina:
    filas: list
    total: int
    numero: int
    por_pagina: int

    @property
    def paginas(self):
        return max(1, (self.total + self.por_pagina - 1) // self.por_pagina)


def dinero(valor):
    return Decimal(valor or 0).quantize(CENTAVOS)


def _nombre_socio():
    return Socio.nombres + " " + Socio.apellidos


def _filtro_socio(filtros):
    condiciones = []
    if filtros.socio:
        # Los comodines introducidos por el usuario se buscan literalmente.
        condiciones.append(_nombre_socio().contains(filtros.socio, autoescape=True))
    if filtros.socio_id:
        condiciones.append(Socio.id == filtros.socio_id)
    return condiciones


def _periodo_fecha(columna, desde, hasta):
    condiciones = []
    if desde:
        condiciones.append(columna >= desde)
    if hasta:
        condiciones.append(columna <= hasta)
    return condiciones


def _periodo_hora(columna, desde, hasta, *, utc=False):
    """Días locales inclusivos; límite superior exclusivo para conservar índices."""
    def limite(fecha):
        hora = datetime.combine(fecha, time.min)
        if utc:
            hora = hora.replace(tzinfo=ZONA_LA_PAZ).astimezone(timezone.utc).replace(tzinfo=None)
        return hora

    condiciones = []
    if desde:
        condiciones.append(columna >= limite(desde))
    if hasta:
        condiciones.append(columna < limite(hasta + timedelta(days=1)))
    return condiciones


def consulta_detalle(filtros):
    """La pantalla y el CSV usan exactamente la misma selección de registros."""
    condiciones = _filtro_socio(filtros)
    if filtros.tipo == "membresias":
        estado = Membresia.expresion_vigencia(filtros.fecha_referencia)
        consulta = db.select(
            Membresia.id, _nombre_socio().label("socio"), Plan.nombre.label("plan"),
            Membresia.fecha_inicio, Membresia.fecha_fin, Membresia.precio_pactado,
            estado.label("estado"),
        ).select_from(Membresia).join(Membresia.socio).join(Membresia.plan)
        if filtros.plan_id:
            condiciones.append(Membresia.plan_id == filtros.plan_id)
        if filtros.estado:
            condiciones.append(estado == filtros.estado)
        condiciones += _periodo_fecha(Membresia.fecha_inicio, filtros.inicio_desde, filtros.inicio_hasta)
        condiciones += _periodo_fecha(Membresia.fecha_fin, filtros.vencimiento_desde, filtros.vencimiento_hasta)
        orden = (Membresia.fecha_inicio.desc(), Membresia.id.desc())
    elif filtros.tipo == "pagos":
        consulta = db.select(
            Pago.id, Pago.fecha_pago, _nombre_socio().label("socio"), Pago.membresia_id,
            Membresia.plan_id, Plan.nombre.label("plan"), Pago.monto,
            Pago.metodo_pago, Pago.referencia, Pago.estado,
        ).select_from(Pago).join(Pago.membresia).join(Membresia.socio).join(Membresia.plan)
        if filtros.plan_id:
            condiciones.append(Membresia.plan_id == filtros.plan_id)
        if filtros.estado:
            condiciones.append(Pago.estado == filtros.estado)
        if filtros.metodo_pago:
            condiciones.append(Pago.metodo_pago == filtros.metodo_pago)
        condiciones += _periodo_hora(Pago.fecha_pago, filtros.fecha_desde, filtros.fecha_hasta, utc=True)
        orden = (Pago.fecha_pago.desc(), Pago.id.desc())
    elif filtros.tipo == "asistencias":
        consulta = db.select(
            Asistencia.id, Asistencia.socio_id, _nombre_socio().label("socio"),
            Asistencia.membresia_id, Asistencia.fecha_hora_entrada,
            Asistencia.fecha_hora_salida, Asistencia.anulada,
            Asistencia.estado.label("estado"),
        ).select_from(Asistencia).join(Asistencia.socio)
        if filtros.membresia_id:
            condiciones.append(Asistencia.membresia_id == filtros.membresia_id)
        if filtros.estado:
            condiciones.append(Asistencia.estado == filtros.estado)
        condiciones += _periodo_hora(Asistencia.fecha_hora_entrada, filtros.fecha_desde, filtros.fecha_hasta)
        orden = (Asistencia.fecha_hora_entrada.desc(), Asistencia.id.desc())
    else:
        raise ValueError("Tipo de reporte no permitido.")
    return consulta.where(*condiciones).order_by(*orden)


def _contar(condicion):
    return func.coalesce(func.sum(case((condicion, 1), else_=0)), 0)


def _paginar(consulta, numero, por_pagina, *, total=None):
    if total is None:
        total = db.session.execute(db.select(func.count()).select_from(consulta.order_by(None).subquery())).scalar_one()
    numero = min(numero, max(1, (total + por_pagina - 1) // por_pagina))
    filas = db.session.execute(consulta.limit(por_pagina).offset((numero - 1) * por_pagina)).mappings().all()
    return Pagina(list(filas), total, numero, por_pagina)


def _resumen(titulo, clave_pagina, columnas, consulta, numero, tamano):
    return {
        "titulo": titulo, "clave_pagina": clave_pagina, "columnas": columnas,
        "pagina": _paginar(consulta, numero, tamano),
    }


def _saldo_actual(filtros):
    # Misma regla que Membresia.saldo_pendiente / total_pagado: precio histórico
    # menos TODOS los pagos válidos. Una fila por membresía evita multiplicarlos.
    pagado = db.select(
        Pago.membresia_id, func.sum(Pago.monto).label("pagado"),
    ).where(Pago.estado == "valido").group_by(Pago.membresia_id).subquery()
    condiciones = _filtro_socio(filtros)
    if filtros.plan_id:
        condiciones.append(Membresia.plan_id == filtros.plan_id)
    consulta = db.select(
        func.coalesce(func.sum(Membresia.precio_pactado - func.coalesce(pagado.c.pagado, 0)), 0),
        func.count(Membresia.id),
    ).select_from(Membresia).join(Membresia.socio).outerjoin(
        pagado, Membresia.id == pagado.c.membresia_id,
    ).where(*condiciones)
    saldo, cantidad = db.session.execute(consulta).one()
    return dinero(saldo), cantidad


def obtener_reporte(filtros):
    with db.session.no_autoflush:
        consulta = consulta_detalle(filtros)
        base = consulta.order_by(None).subquery()
        c = base.c
        resumenes = []
        if filtros.tipo == "membresias":
            proximas = and_(
                c.estado == "vigente",
                c.fecha_fin <= filtros.fecha_referencia + timedelta(days=filtros.dias_por_vencer),
            )
            indicadores = dict(db.session.execute(db.select(
                func.count().label("total"),
                _contar(c.estado == "vigente").label("vigentes"),
                _contar(c.estado == "vencida").label("vencidas"),
                _contar(c.estado == "programada").label("programadas"),
                _contar(c.estado == "cancelada").label("canceladas"),
                _contar(proximas).label("proximas"),
            ).select_from(base)).mappings().one())
            total_filas = indicadores["total"]
        elif filtros.tipo == "pagos":
            valido = c.estado == "valido"
            indicadores = dict(db.session.execute(db.select(
                func.count().label("total_registros"),
                _contar(valido).label("cantidad_pagos"),
                _contar(c.estado == "anulado").label("anulados"),
                func.coalesce(func.sum(case((valido, c.monto), else_=0)), 0).label("ingresos"),
            ).select_from(base)).mappings().one())
            indicadores["ingresos"] = dinero(indicadores["ingresos"])
            indicadores["saldo"], indicadores["membresias_saldo"] = _saldo_actual(filtros)
            metodos = dict(db.session.execute(db.select(
                c.metodo_pago, func.sum(c.monto),
            ).where(valido).group_by(c.metodo_pago)).all())
            resumenes.append({
                "titulo": "Ingresos por método de pago", "clave_pagina": None,
                "columnas": (("metodo", "Método"), ("ingresos", "Ingresos")),
                "pagina": Pagina([
                    {"metodo": metodo, "ingresos": dinero(metodos.get(metodo, 0))}
                    for metodo in METODOS_PAGO
                ], len(METODOS_PAGO), 1, len(METODOS_PAGO)),
            })
            por_plan = db.select(c.plan_id, c.plan, func.sum(c.monto).label("ingresos")).where(valido).group_by(
                c.plan_id, c.plan,
            ).order_by(func.sum(c.monto).desc(), c.plan_id)
            resumenes.append(_resumen(
                "Ingresos por plan", "pagina_planes", (("plan", "Plan"), ("ingresos", "Ingresos")),
                por_plan, filtros.pagina_planes, filtros.por_pagina,
            ))
            total_filas = indicadores["total_registros"]
        else:
            valida = c.anulada.is_(False)
            indicadores = dict(db.session.execute(db.select(
                func.count().label("total_registros"),
                _contar(valida).label("total"),
                func.count(distinct(case((valida, c.socio_id), else_=None))).label("socios_unicos"),
                _contar(and_(valida, c.fecha_hora_salida.is_(None))).label("abiertas"),
                _contar(and_(valida, c.fecha_hora_salida >= c.fecha_hora_entrada)).label("cerradas"),
            ).select_from(base)).mappings().one())
            por_socio = db.select(c.socio_id, c.socio, func.count().label("asistencias")).where(valida).group_by(
                c.socio_id, c.socio,
            ).order_by(func.count().desc(), c.socio_id)
            dia = func.date(c.fecha_hora_entrada)
            por_dia = db.select(dia.label("fecha"), func.count().label("asistencias")).where(valida).group_by(dia).order_by(dia.desc())
            resumenes += [
                _resumen("Frecuencia por socio", "pagina_socios",
                         (("socio", "Socio"), ("asistencias", "Asistencias")),
                         por_socio, filtros.pagina_socios, filtros.por_pagina),
                _resumen("Asistencias por día", "pagina_diaria",
                         (("fecha", "Fecha"), ("asistencias", "Asistencias")),
                         por_dia, filtros.pagina_diaria, filtros.por_pagina),
            ]
            total_filas = indicadores["total_registros"]
        pagina = _paginar(consulta, filtros.pagina, filtros.por_pagina, total=total_filas)
        pagina.filas = [presentar_fila(fila, filtros) for fila in pagina.filas]
        return {"indicadores": indicadores, "pagina": pagina, "resumenes": resumenes}


def presentar_fila(fila, filtros):
    fila = dict(fila)
    if filtros.tipo == "membresias":
        fila["dias_restantes"] = (
            (fila["fecha_fin"] - filtros.fecha_referencia).days
            if fila["estado"] == "vigente" else None
        )
    elif filtros.tipo == "pagos":
        fila["fecha_pago"] = fila["fecha_pago"].replace(tzinfo=timezone.utc).astimezone(ZONA_LA_PAZ).replace(tzinfo=None)
    else:
        fila["fecha"] = fila["fecha_hora_entrada"].date()
        fila["entrada"] = fila["fecha_hora_entrada"].time()
        fila["salida"] = fila["fecha_hora_salida"]
    return fila


def filas_exportacion(filtros):
    """Recorre todas las filas filtradas por lotes, sin límites de página."""
    with db.session.no_autoflush:
        resultado = db.session.execute(consulta_detalle(filtros).execution_options(yield_per=500))
        try:
            for fila in resultado.mappings():
                yield presentar_fila(fila, filtros)
        finally:
            resultado.close()
