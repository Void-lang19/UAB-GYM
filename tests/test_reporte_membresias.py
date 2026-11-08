import codecs
import csv
from datetime import date
from io import StringIO

from app import db
from app.models import Membresia
from tests._reportes_support import REFERENCIA, ReporteDatosTest


class ReporteMembresiasTests(ReporteDatosTest):
    def test_categorias_excluyentes_y_proximas_como_subconjunto(self):
        with self.solo_lectura():
            resultado = self.reporte("membresias")
            self.assertEqual(resultado["indicadores"], {
                "total": 5, "vigentes": 2, "vencidas": 1,
                "programadas": 1, "canceladas": 1, "proximas": 1,
            })
            for fila in resultado["pagina"].filas:
                modelo = db.session.get(Membresia, fila["id"])
                self.assertEqual(fila["estado"], modelo.vigencia_en(REFERENCIA))
            self.csv("membresias")

    def test_fecha_referencia_y_ventana_configurable(self):
        self.assertEqual(self.reporte("membresias", dias_por_vencer=6)["indicadores"]["proximas"], 0)
        referencia = "2026-11-15"
        resultado = self.reporte("membresias", fecha_referencia=referencia, dias_por_vencer=0)
        self.assertEqual(resultado["indicadores"]["proximas"], 1)
        proxima = next(f for f in resultado["pagina"].filas if f["id"] == self.datos["proxima"].id)
        self.assertEqual(proxima["dias_restantes"], 0)
        self.assertEqual(proxima["estado"], "vigente")
        self.assertEqual(self.reporte("membresias", fecha_referencia="2026-11-16")["indicadores"]["vencidas"], 2)

    def test_filtros_por_socio_plan_estado_y_fechas_independientes(self):
        resultado = self.reporte("membresias", socio="Ana", plan_id=self.datos["mensual"].id, estado="vigente")
        self.assertEqual([f["id"] for f in resultado["pagina"].filas], [self.datos["vigente"].id])
        self.assertEqual(self.reporte("membresias", socio_id=self.datos["bruno"].id)["indicadores"]["total"], 2)
        self.assertEqual(self.reporte("membresias", inicio_desde="2026-11-01", inicio_hasta="2026-11-08")["indicadores"]["total"], 3)
        self.assertEqual(self.reporte("membresias", vencimiento_desde="2026-11-01", vencimiento_hasta="2026-11-15")["indicadores"]["total"], 1)
        self.assertEqual(self.reporte("membresias", socio="%")["indicadores"]["total"], 0)

    def test_vacio_y_csv_con_encabezados_sin_documentos(self):
        resultado = self.reporte("membresias", socio="Sin coincidencias")
        self.assertTrue(all(v == 0 for v in resultado["indicadores"].values()))
        self.assertEqual(resultado["pagina"].filas, [])
        contenido = self.csv("membresias", estado="vigente")
        self.assertTrue(contenido.startswith(codecs.BOM_UTF8))
        filas = list(csv.DictReader(StringIO(contenido.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(filas), 2)
        self.assertEqual({f["Estado"] for f in filas}, {"vigente"})
        self.assertNotIn("Documento", filas[0])
        self.assertNotIn(b"PRUEBA-ANA", contenido)

    def test_totales_y_exportacion_no_se_limitan_a_la_pagina(self):
        for _ in range(12):
            db.session.add(Membresia(
                socio_id=self.datos["ana"].id, plan_id=self.datos["mensual"].id,
                fecha_inicio=date(2020, 1, 1), fecha_fin=date(2020, 1, 30),
                precio_pactado=self.datos["mensual"].precio, estado="cancelada",
            ))
        db.session.commit()
        with self.solo_lectura():
            resultado = self.reporte("membresias", por_pagina=10)
            self.assertEqual(resultado["indicadores"]["total"], 17)
            self.assertEqual(len(resultado["pagina"].filas), 10)
            self.assertEqual(resultado["pagina"].paginas, 2)
            texto = self.csv("membresias", por_pagina=10, pagina=2).decode("utf-8-sig")
            self.assertEqual(len(list(csv.DictReader(StringIO(texto), delimiter=";"))), 17)
