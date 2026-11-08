"""Fixtures aisladas en SQLite en memoria. No utiliza .env ni la base real."""

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import unittest

from flask import Flask
from sqlalchemy import event

from app import db
from app.models import Asistencia, Membresia, Pago, Plan, Socio
from app.reportes_csv import crear_archivo_csv
from app.reportes_filtros import validar_filtros
from app.services_reportes import COLUMNAS, filas_exportacion, obtener_reporte

REFERENCIA = date(2026, 11, 8)


def sembrar_reportes():
    ana = Socio(nombres="Ana", apellidos="Pérez", documento_identidad="PRUEBA-ANA")
    bruno = Socio(nombres="Bruno", apellidos="López", documento_identidad="PRUEBA-BRUNO")
    mensual = Plan(nombre="Mensual prueba", duracion_dias=30, precio=Decimal("200.00"))
    semanal = Plan(nombre="Semanal prueba", duracion_dias=7, precio=Decimal("50.00"))
    db.session.add_all([ana, bruno, mensual, semanal])
    db.session.flush()

    def contrato(socio, plan, inicio, fin, precio, estado="activa"):
        objeto = Membresia(
            socio=socio, plan=plan, fecha_inicio=date.fromisoformat(inicio),
            fecha_fin=date.fromisoformat(fin), precio_pactado=Decimal(precio), estado=estado,
        )
        db.session.add(objeto)
        return objeto

    vigente = contrato(ana, mensual, "2026-11-01", "2026-11-30", "200")
    proxima = contrato(bruno, semanal, "2026-11-08", "2026-11-15", "50")
    vencida = contrato(ana, mensual, "2026-10-01", "2026-10-30", "200")
    programada = contrato(bruno, mensual, "2026-12-01", "2026-12-30", "200")
    cancelada = contrato(ana, semanal, "2026-11-01", "2026-11-30", "50", "cancelada")
    db.session.flush()
    pagos = [
        (vigente, "2026-11-08 04:00:00", "100.00", "Efectivo", "valido"),
        (vigente, "2026-11-09 03:59:59", "50.25", "QR", "valido"),
        (vigente, "2026-11-08 15:00:00", "20.00", "QR", "anulado"),
        (cancelada, "2026-11-08 12:00:00", "12.10", "Transferencia bancaria", "valido"),
        (vencida, "2026-11-08 03:59:59", "10.00", "Efectivo", "valido"),
        (proxima, "2026-11-09 04:00:00", "5.00", "Otro", "valido"),
    ]
    for membresia, fecha, monto, metodo, estado in pagos:
        db.session.add(Pago(
            membresia=membresia, fecha_pago=datetime.fromisoformat(fecha),
            monto=Decimal(monto), metodo_pago=metodo, estado=estado,
            referencia="Comprobante de prueba",
        ))
    asistencias = [
        (ana, vigente, "2026-11-08 00:00:00", None, False),
        (bruno, proxima, "2026-11-08 10:00:00", "2026-11-08 11:00:00", False),
        (bruno, proxima, "2026-11-08 23:59:59", "2026-11-09 01:00:00", False),
        (ana, vigente, "2026-11-08 14:00:00", None, True),
        (ana, vigente, "2026-11-07 23:59:59", "2026-11-08 00:00:00", False),
        (bruno, proxima, "2026-11-09 00:00:00", None, False),
    ]
    for socio, membresia, entrada, salida, anulada in asistencias:
        db.session.add(Asistencia(
            socio=socio, membresia=membresia, fecha_hora_entrada=datetime.fromisoformat(entrada),
            fecha_hora_salida=datetime.fromisoformat(salida) if salida else None, anulada=anulada,
        ))
    db.session.commit()
    return {"ana": ana, "bruno": bruno, "mensual": mensual, "semanal": semanal,
            "vigente": vigente, "proxima": proxima, "vencida": vencida,
            "programada": programada, "cancelada": cancelada}


class ReporteDatosTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False)
        db.init_app(self.app)
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()
        self.datos = sembrar_reportes()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.contexto.pop()

    def filtros(self, tipo, **parametros):
        if tipo == "membresias":
            parametros.setdefault("fecha_referencia", REFERENCIA.isoformat())
        return validar_filtros(tipo, {k: str(v) for k, v in parametros.items()})

    def reporte(self, tipo, **parametros):
        return obtener_reporte(self.filtros(tipo, **parametros))

    def csv(self, tipo, **parametros):
        filtros = self.filtros(tipo, **parametros)
        with crear_archivo_csv(COLUMNAS[tipo], filas_exportacion(filtros)) as archivo:
            return archivo.read()

    def foto(self):
        return {
            modelo.__tablename__: db.session.execute(db.select(modelo.__table__).order_by(modelo.id)).all()
            for modelo in (Socio, Plan, Membresia, Pago, Asistencia)
        }

    @contextmanager
    def solo_lectura(self):
        antes = self.foto()
        escrituras = []

        def registrar(_conexion, _cursor, sql, _parametros, _contexto, _muchos):
            if sql.lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"}:
                escrituras.append(sql)

        event.listen(db.engine, "before_cursor_execute", registrar)
        try:
            yield
            self.assertEqual(self.foto(), antes)
            self.assertEqual(escrituras, [])
            self.assertFalse(db.session.new or db.session.dirty or db.session.deleted)
        finally:
            event.remove(db.engine, "before_cursor_execute", registrar)
