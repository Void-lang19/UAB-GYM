"""Carga idempotente de registros ficticios para probar las pantallas."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app import db
from app.models import Asistencia, Entrenador, Membresia, Pago, Plan, Socio
from app.timeutils import ZONA_LA_PAZ

SOCIOS_ANTERIORES = {
    "DEMO-UAB-001": ("9230411", "Ana Lucía", "Rojas", "ana.rojas@example.com"),
    "DEMO-UAB-002": ("8326154", "Bruno Andrés", "Mendoza", "bruno.mendoza@example.com"),
    "DEMO-UAB-003": ("7612938", "Camila Fernanda", "Vargas", "camila.vargas@example.com"),
}
ENTRENADORES_ANTERIORES = {
    "DEMO-ENT-001": ("7142086", "Marcos", "Salvatierra", "marcos.salvatierra@example.com"),
    "DEMO-ENT-002": ("6983742", "Paola", "Ribera", "paola.ribera@example.com"),
}
PLANES_ANTERIORES = {
    "DEMO - Mensual": "Mensual 30 días",
    "DEMO - Trimestral": "Trimestral 90 días",
    "DEMO - Semanal": "Semanal 7 días",
}
MEMBRESIAS_ANTERIORES = {
    "[DEMO UAB-GYM] membresía ana-mensual": "Membresía mensual de Ana Lucía Rojas",
    "[DEMO UAB-GYM] membresía bruno-trimestral": "Membresía trimestral de Bruno Andrés Mendoza",
    "[DEMO UAB-GYM] membresía camila-historica": "Membresía finalizada de Camila Fernanda Vargas",
}
PAGOS_ANTERIORES = {
    "DEMO-ANA-1": ("REC-2026-1041", "Abono de membresía"),
    "DEMO-ANA-2": ("REC-2026-1042", "Abono de membresía"),
    "DEMO-BRUNO-1": ("REC-2026-1043", "Abono de membresía"),
    "DEMO-BRUNO-2": ("REC-2026-1044", "Pago anulado"),
}
ASISTENCIAS_ANTERIORES = {
    "[DEMO UAB-GYM] asistencia ana-ayer": "Ingreso de la tarde",
    "[DEMO UAB-GYM] asistencia ana-hoy": "Entrenamiento de la mañana",
    "[DEMO UAB-GYM] asistencia bruno-abierta": "Sesión en curso",
}


def _socio(documento: str, nombres: str, apellidos: str, nacimiento: date, correo: str) -> tuple[Socio, bool]:
    actual = db.session.execute(
        db.select(Socio).where(Socio.documento_identidad == documento)
    ).scalar_one_or_none()
    if actual:
        return actual, False
    actual = Socio(
        nombres=nombres, apellidos=apellidos, documento_identidad=documento,
        telefono="70000000", correo_electronico=correo,
        fecha_nacimiento=nacimiento, direccion="Vinto, Cochabamba",
        fecha_registro=date.today(), estado="activo",
    )
    db.session.add(actual)
    db.session.flush()
    return actual, True


def _entrenador(documento: str, nombres: str, apellidos: str, especialidad: str, correo: str) -> tuple[Entrenador, bool]:
    actual = db.session.execute(
        db.select(Entrenador).where(Entrenador.documento_identidad == documento)
    ).scalar_one_or_none()
    if actual:
        return actual, False
    actual = Entrenador(
        nombres=nombres, apellidos=apellidos, documento_identidad=documento,
        telefono="70000001", correo_electronico=correo,
        especialidad=especialidad, fecha_contratacion=date.today() - timedelta(days=365),
        estado="activo",
    )
    db.session.add(actual)
    db.session.flush()
    return actual, True


def _plan(nombre: str, dias: int, precio: Decimal, descripcion: str) -> tuple[Plan, bool]:
    actual = db.session.execute(db.select(Plan).where(Plan.nombre == nombre)).scalar_one_or_none()
    if actual:
        return actual, False
    actual = Plan(
        nombre=nombre, duracion_dias=dias, precio=precio,
        descripcion=descripcion, beneficios="Acceso a instalaciones del gimnasio",
        estado="activo",
    )
    db.session.add(actual)
    db.session.flush()
    return actual, True


def _membresia(socio: Socio, plan: Plan, inicio: date, estado: str, etiqueta: str) -> tuple[Membresia, bool]:
    observacion = etiqueta
    actual = db.session.execute(
        db.select(Membresia).where(Membresia.observaciones == observacion)
    ).scalar_one_or_none()
    if actual:
        return actual, False
    actual = Membresia(
        socio_id=socio.id, plan_id=plan.id, fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(days=plan.duracion_dias - 1),
        precio_pactado=plan.precio, estado=estado, observaciones=observacion,
    )
    db.session.add(actual)
    db.session.flush()
    return actual, True


def _pago(membresia: Membresia, referencia: str, monto: Decimal, metodo: str, estado: str = "valido") -> bool:
    referencia_demo = f"REC-{referencia}"
    actual = db.session.execute(
        db.select(Pago.id).where(Pago.referencia == referencia_demo)
    ).first()
    if actual:
        return False
    db.session.add(Pago(
        membresia_id=membresia.id, fecha_pago=datetime.now(ZONA_LA_PAZ).replace(tzinfo=None),
        monto=monto, metodo_pago=metodo, referencia=referencia_demo,
        estado=estado, observaciones="Abono de membresía",
        fecha_anulacion=datetime.now(ZONA_LA_PAZ).replace(tzinfo=None) if estado == "anulado" else None,
        motivo_anulacion="Pago anulado" if estado == "anulado" else None,
    ))
    db.session.flush()
    return True


def _asistencia(socio: Socio, membresia: Membresia, etiqueta: str, cuando: datetime, salida: datetime | None) -> bool:
    observacion = etiqueta
    actual = db.session.execute(
        db.select(Asistencia.id).where(Asistencia.observaciones == observacion)
    ).first()
    if actual:
        return False
    db.session.add(Asistencia(
        socio_id=socio.id, membresia_id=membresia.id,
        fecha_hora_entrada=cuando, fecha_hora_salida=salida,
        observaciones=observacion, anulada=False,
    ))
    db.session.flush()
    return True


def _actualizar_registros_anteriores() -> None:
    """Quita marcas visibles de cargas anteriores, sin tocar otros registros."""
    for documento_anterior, datos in SOCIOS_ANTERIORES.items():
        socio = db.session.execute(db.select(Socio).where(
            Socio.documento_identidad == documento_anterior,
        )).scalar_one_or_none()
        if socio is None:
            continue
        documento, nombres, apellidos, correo = datos
        conflicto = db.session.execute(db.select(Socio.id).where(
            Socio.documento_identidad == documento, Socio.id != socio.id,
        )).first()
        if conflicto:
            raise ValueError("No se puede normalizar un socio porque su documento ya está en uso.")
        socio.documento_identidad = documento
        socio.nombres, socio.apellidos = nombres, apellidos
        socio.correo_electronico = correo

    for documento_anterior, datos in ENTRENADORES_ANTERIORES.items():
        entrenador = db.session.execute(db.select(Entrenador).where(
            Entrenador.documento_identidad == documento_anterior,
        )).scalar_one_or_none()
        if entrenador is None:
            continue
        documento, nombres, apellidos, correo = datos
        conflicto = db.session.execute(db.select(Entrenador.id).where(
            Entrenador.documento_identidad == documento, Entrenador.id != entrenador.id,
        )).first()
        if conflicto:
            raise ValueError("No se puede normalizar un entrenador porque su documento ya está en uso.")
        entrenador.documento_identidad = documento
        entrenador.nombres, entrenador.apellidos = nombres, apellidos
        entrenador.correo_electronico = correo

    for nombre_anterior, nombre_nuevo in PLANES_ANTERIORES.items():
        plan = db.session.execute(db.select(Plan).where(Plan.nombre == nombre_anterior)).scalar_one_or_none()
        if plan is None:
            continue
        conflicto = db.session.execute(db.select(Plan.id).where(
            Plan.nombre == nombre_nuevo, Plan.id != plan.id,
        )).first()
        if conflicto:
            raise ValueError("No se puede normalizar un plan porque ese nombre ya está en uso.")
        plan.nombre = nombre_nuevo
        plan.descripcion = f"Plan de acceso por {plan.duracion_dias} días"
        plan.beneficios = "Acceso a instalaciones del gimnasio"

    for anterior, nuevo in MEMBRESIAS_ANTERIORES.items():
        membresia = db.session.execute(db.select(Membresia).where(
            Membresia.observaciones == anterior,
        )).scalar_one_or_none()
        if membresia:
            membresia.observaciones = nuevo

    for anterior, (nuevo, observaciones) in PAGOS_ANTERIORES.items():
        pago = db.session.execute(db.select(Pago).where(Pago.referencia == anterior)).scalar_one_or_none()
        if pago:
            pago.referencia = nuevo
            pago.observaciones = observaciones
            if pago.estado == "anulado":
                pago.motivo_anulacion = "Pago anulado"

    for anterior, nuevo in ASISTENCIAS_ANTERIORES.items():
        asistencia = db.session.execute(db.select(Asistencia).where(
            Asistencia.observaciones == anterior,
        )).scalar_one_or_none()
        if asistencia:
            asistencia.observaciones = nuevo


def cargar_datos_demo() -> dict[str, int]:
    """Agrega ejemplos de cada módulo sin cambiar ni duplicar registros existentes."""
    hoy = datetime.now(ZONA_LA_PAZ).date()
    creados = {"socios": 0, "entrenadores": 0, "planes": 0, "membresias": 0, "pagos": 0, "asistencias": 0}
    try:
        _actualizar_registros_anteriores()
        ana, nuevo = _socio("9230411", "Ana Lucía", "Rojas", date(2001, 4, 12), "ana.rojas@example.com")
        creados["socios"] += nuevo
        bruno, nuevo = _socio("8326154", "Bruno Andrés", "Mendoza", date(1998, 9, 3), "bruno.mendoza@example.com")
        creados["socios"] += nuevo
        camila, nuevo = _socio("7612938", "Camila Fernanda", "Vargas", date(2003, 1, 26), "camila.vargas@example.com")
        creados["socios"] += nuevo
        _, nuevo = _entrenador("7142086", "Marcos", "Salvatierra", "Entrenamiento funcional", "marcos.salvatierra@example.com")
        creados["entrenadores"] += nuevo
        _, nuevo = _entrenador("6983742", "Paola", "Ribera", "Acondicionamiento físico", "paola.ribera@example.com")
        creados["entrenadores"] += nuevo

        mensual, nuevo = _plan("Mensual 30 días", 30, Decimal("150.00"), "Plan de acceso por 30 días")
        creados["planes"] += nuevo
        trimestral, nuevo = _plan("Trimestral 90 días", 90, Decimal("390.00"), "Plan de acceso por 90 días")
        creados["planes"] += nuevo
        _, nuevo = _plan("Semanal 7 días", 7, Decimal("50.00"), "Plan de acceso por 7 días")
        creados["planes"] += nuevo

        membresia_ana, nuevo = _membresia(ana, mensual, hoy - timedelta(days=12), "activa", "Membresía mensual de Ana Lucía Rojas")
        creados["membresias"] += nuevo
        membresia_bruno, nuevo = _membresia(bruno, trimestral, hoy - timedelta(days=35), "activa", "Membresía trimestral de Bruno Andrés Mendoza")
        creados["membresias"] += nuevo
        membresia_camila, nuevo = _membresia(camila, mensual, hoy - timedelta(days=75), "cancelada", "Membresía finalizada de Camila Fernanda Vargas")
        creados["membresias"] += nuevo

        creados["pagos"] += _pago(membresia_ana, "2026-1041", Decimal("100.00"), "Efectivo")
        creados["pagos"] += _pago(membresia_ana, "2026-1042", Decimal("50.00"), "QR")
        creados["pagos"] += _pago(membresia_bruno, "2026-1043", Decimal("200.00"), "Transferencia bancaria")
        creados["pagos"] += _pago(membresia_bruno, "2026-1044", Decimal("25.00"), "Otro", "anulado")

        ayer = hoy - timedelta(days=1)
        ahora = datetime.now(ZONA_LA_PAZ).replace(tzinfo=None)
        creados["asistencias"] += _asistencia(
            ana, membresia_ana, "Ingreso de la tarde",
            datetime.combine(ayer, time(18, 10)), datetime.combine(ayer, time(19, 5)),
        )
        creados["asistencias"] += _asistencia(
            ana, membresia_ana, "Entrenamiento de la mañana", ahora - timedelta(hours=2), ahora - timedelta(hours=1),
        )
        creados["asistencias"] += _asistencia(
            bruno, membresia_bruno, "Sesión en curso", ahora, None,
        )
        db.session.commit()
        return creados
    except Exception:
        db.session.rollback()
        raise
