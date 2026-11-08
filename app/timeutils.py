"""Reloj civil de La Paz sin depender del huso horario del servidor."""

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    ZONA_LA_PAZ = ZoneInfo("America/La_Paz")
except ZoneInfoNotFoundError:  # Windows puede no incluir la base IANA del sistema.
    ZONA_LA_PAZ = timezone(timedelta(hours=-4), "America/La_Paz")
