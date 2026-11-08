"""Validación de parámetros GET de los reportes (sin escrituras)."""

from dataclasses import dataclass
from datetime import date, datetime
import re

from app import db
from app.models import Membresia, Plan, Socio
from app.services import METODOS_PAGO
from app.timeutils import ZONA_LA_PAZ

ESTADOS_MEMBRESIA = ("vigente", "vencida", "programada", "cancelada")
ESTADOS_PAGO = ("valido", "anulado")
ESTADOS_ASISTENCIA = ("abierta", "cerrada", "anulada")


class FiltroInvalido(ValueError):
    """Error de parámetros que puede mostrarse al usuario sin datos internos."""


@dataclass(frozen=True)
class FiltrosReporte:
    tipo: str
    socio: str = ""
    socio_id: int | None = None
    plan_id: int | None = None
    membresia_id: int | None = None
    estado: str = ""
    metodo_pago: str = ""
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    inicio_desde: date | None = None
    inicio_hasta: date | None = None
    vencimiento_desde: date | None = None
    vencimiento_hasta: date | None = None
    fecha_referencia: date | None = None
    dias_por_vencer: int = 7
    pagina: int = 1
    por_pagina: int = 25
    pagina_planes: int = 1
    pagina_diaria: int = 1
    pagina_socios: int = 1


COMUNES = {"socio", "socio_id", "estado", "pagina", "por_pagina"}
PARAMETROS = {
    "membresias": COMUNES | {
        "plan_id", "inicio_desde", "inicio_hasta", "vencimiento_desde",
        "vencimiento_hasta", "fecha_referencia", "dias_por_vencer",
    },
    "pagos": COMUNES | {
        "plan_id", "metodo_pago", "fecha_desde", "fecha_hasta", "pagina_planes",
    },
    "asistencias": COMUNES | {
        "membresia_id", "fecha_desde", "fecha_hasta", "pagina_diaria", "pagina_socios",
    },
}


def _entero(valor, nombre, minimo=1, maximo=2_147_483_647):
    if not re.fullmatch(r"[0-9]{1,10}", valor):
        raise FiltroInvalido(f"{nombre}: introduce un número entero válido.")
    numero = int(valor)
    if not minimo <= numero <= maximo:
        raise FiltroInvalido(f"{nombre}: debe estar entre {minimo} y {maximo}.")
    return numero


def _fecha(valor, nombre):
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", valor):
            raise ValueError
        resultado = date.fromisoformat(valor)
        # Límites compatibles con MySQL, conversión UTC y suma de hasta 365 días.
        if not 1900 <= resultado.year <= 9998:
            raise ValueError
        return resultado
    except ValueError:
        raise FiltroInvalido(f"{nombre}: utiliza una fecha válida AAAA-MM-DD (1900–9998).") from None


def validar_filtros(tipo, parametros, *, dias_predeterminados=7):
    if tipo not in PARAMETROS:
        raise FiltroInvalido("El reporte solicitado no existe.")
    valores = {}
    for clave in parametros:
        if clave not in PARAMETROS[tipo]:
            raise FiltroInvalido("La consulta contiene un parámetro no permitido.")
        if hasattr(parametros, "getlist") and len(parametros.getlist(clave)) != 1:
            raise FiltroInvalido("No se permite repetir un parámetro de búsqueda.")
        valor = parametros.get(clave)
        if not isinstance(valor, str) or len(valor) > 120:
            raise FiltroInvalido("Un parámetro tiene un formato o tamaño no permitido.")
        valores[clave] = valor.strip()

    datos = {"tipo": tipo}
    texto = valores.get("socio", "")
    if len(texto) > 100 or any(ord(c) < 32 or ord(c) == 127 for c in texto):
        raise FiltroInvalido("Socio: utiliza hasta 100 caracteres sin controles.")
    datos["socio"] = texto
    estados = {
        "membresias": ESTADOS_MEMBRESIA,
        "pagos": ESTADOS_PAGO,
        "asistencias": ESTADOS_ASISTENCIA,
    }
    for clave, opciones in (("estado", estados[tipo]), ("metodo_pago", METODOS_PAGO)):
        valor = valores.get(clave, "")
        if valor and valor not in opciones:
            raise FiltroInvalido(f"{clave}: selecciona una opción permitida.")
        datos[clave] = valor

    for clave, modelo in (("socio_id", Socio), ("plan_id", Plan), ("membresia_id", Membresia)):
        if valores.get(clave):
            identificador = _entero(valores[clave], clave)
            with db.session.no_autoflush:
                existe = db.session.execute(db.select(modelo.id).where(modelo.id == identificador)).first()
            if not existe:
                raise FiltroInvalido(f"{clave}: el registro seleccionado no existe.")
            datos[clave] = identificador

    for clave in ("fecha_desde", "fecha_hasta", "inicio_desde", "inicio_hasta",
                  "vencimiento_desde", "vencimiento_hasta", "fecha_referencia"):
        if valores.get(clave):
            datos[clave] = _fecha(valores[clave], clave)
    for desde, hasta in (("fecha_desde", "fecha_hasta"), ("inicio_desde", "inicio_hasta"),
                         ("vencimiento_desde", "vencimiento_hasta")):
        if datos.get(desde) and datos.get(hasta) and datos[desde] > datos[hasta]:
            raise FiltroInvalido(f"{desde} no puede ser posterior a {hasta}.")

    for clave in ("pagina", "pagina_planes", "pagina_diaria", "pagina_socios", "por_pagina"):
        if valores.get(clave):
            datos[clave] = _entero(valores[clave], clave, maximo=1_000_000)
    if datos.get("por_pagina", 25) not in (10, 25, 50, 100):
        raise FiltroInvalido("El tamaño de página debe ser 10, 25, 50 o 100.")
    if tipo == "membresias":
        datos.setdefault("fecha_referencia", datetime.now(ZONA_LA_PAZ).date())
        datos["dias_por_vencer"] = _entero(
            valores.get("dias_por_vencer") or str(dias_predeterminados),
            "dias_por_vencer", minimo=0, maximo=365,
        )
    return FiltrosReporte(**datos)
