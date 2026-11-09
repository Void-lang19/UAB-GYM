import codecs
import csv
from decimal import Decimal
from io import StringIO

from werkzeug.datastructures import MultiDict
from sqlalchemy import event

from app import db
from app.models import Pago
from app.reportes_csv import celda_segura, crear_archivo_csv
from app.reportes_filtros import FiltroInvalido, validar_filtros
from tests._reportes_support import ReporteDatosTest


class ReportesFiltrosCsvTests(ReporteDatosTest):
    def test_numero_de_consultas_acotado_sin_cargar_relaciones_por_fila(self):
        for tipo, maximo in (("membresias", 2), ("pagos", 6), ("asistencias", 6)):
            consultas = []

            def registrar(_conexion, _cursor, sql, _parametros, _contexto, _muchos):
                if sql.lstrip().upper().startswith("SELECT"):
                    consultas.append(sql)

            event.listen(db.engine, "before_cursor_execute", registrar)
            try:
                with self.subTest(tipo=tipo):
                    self.reporte(tipo)
                    self.assertLessEqual(len(consultas), maximo)
            finally:
                event.remove(db.engine, "before_cursor_execute", registrar)

    def test_rechaza_fechas_invertidas_malformadas_y_fuera_de_rango(self):
        casos = (
            ("pagos", {"fecha_desde": "2026-02-30"}),
            ("pagos", {"fecha_desde": "08/11/2026"}),
            ("asistencias", {"fecha_hasta": "9999-12-31"}),
            ("pagos", {"fecha_desde": "2026-11-09", "fecha_hasta": "2026-11-08"}),
            ("membresias", {"inicio_desde": "2026-11-09", "inicio_hasta": "2026-11-08"}),
            ("membresias", {"vencimiento_desde": "2026-11-09", "vencimiento_hasta": "2026-11-08"}),
        )
        for tipo, parametros in casos:
            with self.subTest(tipo=tipo, parametros=parametros), self.assertRaises(FiltroInvalido):
                validar_filtros(tipo, parametros)

    def test_identificadores_opciones_paginacion_y_busquedas_invalidas(self):
        casos = (
            {"socio_id": "999999"}, {"plan_id": "999999"}, {"socio_id": "-1"},
            {"socio_id": "1 OR 1=1"}, {"estado": "inventado"}, {"metodo_pago": "Tarjeta"},
            {"pagina": "0"}, {"pagina": "-1"}, {"pagina": "1.5"}, {"por_pagina": "100000"},
            {"socio": "a" * 101}, {"socio": "Ana\x00"}, {"orden_sql": "id"},
        )
        for parametros in casos:
            with self.subTest(parametros=parametros), self.assertRaises(FiltroInvalido):
                validar_filtros("pagos", parametros)
        with self.assertRaises(FiltroInvalido):
            validar_filtros("asistencias", {"membresia_id": "999999"})
        with self.assertRaises(FiltroInvalido):
            validar_filtros("pagos", MultiDict([("estado", "valido"), ("estado", "anulado")]))
        for dias in ("-1", "366", "no"):
            with self.subTest(dias=dias), self.assertRaises(FiltroInvalido):
                validar_filtros("membresias", {"dias_por_vencer": dias})

    def test_filtros_vacios_son_opcionales_y_configuracion_de_ventana(self):
        filtros = validar_filtros("pagos", {"socio": " ", "plan_id": "", "fecha_desde": "", "estado": ""})
        self.assertIsNone(filtros.plan_id)
        self.assertIsNone(filtros.fecha_desde)
        self.assertEqual(filtros.estado, "")
        self.assertEqual(validar_filtros("membresias", {}, dias_predeterminados=14).dias_por_vencer, 14)

    def test_csv_bom_comillas_unicode_y_formulas_tras_espacios(self):
        for texto in ("=1+1", "+SUM(A1)", "-1+2", "@SUM(A1)", "  =1+1", "\t=1+1", "\r=1+1", "\n@x", "\ufeff=1", "\u00a0=1"):
            with self.subTest(texto=texto):
                self.assertEqual(celda_segura(texto), "'" + texto)
        self.assertEqual(celda_segura(Decimal("-10.25")), "-10.25")
        self.assertEqual(celda_segura("Ana Pérez"), "Ana Pérez")
        with crear_archivo_csv((("texto", "Texto"), ("monto", "Monto")), [
            {"texto": 'Pérez; "prueba"\nsegunda línea', "monto": Decimal("12.10")},
        ]) as archivo:
            contenido = archivo.read()
        self.assertTrue(contenido.startswith(codecs.BOM_UTF8))
        fila = next(csv.DictReader(StringIO(contenido.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(fila["Texto"], 'Pérez; "prueba"\nsegunda línea')
        self.assertEqual(fila["Monto"], "12.10")

    def test_exportar_neutraliza_datos_sin_alterar_originales(self):
        self.datos["ana"].nombres = "=SUM(1)"
        pago = db.session.execute(db.select(Pago).order_by(Pago.id)).scalars().first()
        pago.referencia = "\t=1+1"
        db.session.commit()
        with self.solo_lectura():
            texto = self.csv("pagos").decode("utf-8-sig")
            self.assertIn("'=SUM(1) Pérez", texto)
            self.assertIn("'\t=1+1", texto)
            self.assertEqual(pago.referencia, "\t=1+1")
