"""CSV con BOM UTF-8 y neutralización de fórmulas; nunca altera los datos."""

import csv
from datetime import date, datetime, time
from decimal import Decimal
from io import TextIOWrapper
from tempfile import SpooledTemporaryFile


def formatear_valor(valor):
    if valor is None:
        return ""
    if isinstance(valor, Decimal):
        return format(valor, ".2f")
    if isinstance(valor, datetime):
        return valor.isoformat(sep=" ", timespec="seconds")
    if isinstance(valor, time):
        return valor.isoformat(timespec="seconds")
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)


def celda_segura(valor):
    texto = formatear_valor(valor)
    if isinstance(valor, str):
        inicio = texto.lstrip()
        while inicio.startswith("\ufeff"):
            inicio = inicio[1:].lstrip()
        if inicio.startswith(("=", "+", "-", "@")) or texto.startswith(("\t", "\r", "\n")):
            return "'" + texto
    return texto


def crear_archivo_csv(columnas, filas):
    # Se vuelca a disco temporal si supera 1 MiB. Finaliza antes de enviar HTTP
    # para devolver un error seguro en lugar de una descarga exitosa incompleta.
    archivo = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
    texto = TextIOWrapper(archivo, encoding="utf-8-sig", newline="")
    try:
        escritor = csv.writer(texto, delimiter=";", lineterminator="\r\n")
        escritor.writerow([titulo for _, titulo in columnas])
        for fila in filas:
            escritor.writerow([celda_segura(fila[clave]) for clave, _ in columnas])
        texto.flush()
    except BaseException:
        texto.close()
        raise
    texto.detach()
    archivo.seek(0)
    return archivo
