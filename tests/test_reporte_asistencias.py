import csv
from io import StringIO

from tests._reportes_support import ReporteDatosTest


class ReporteAsistenciasTests(ReporteDatosTest):
    def test_validas_socios_unicos_estados_y_limites_del_dia(self):
        with self.solo_lectura():
            resultado = self.reporte("asistencias", fecha_desde="2026-11-08", fecha_hasta="2026-11-08")
            self.assertEqual(resultado["indicadores"], {
                "total_registros": 4, "total": 3, "socios_unicos": 2,
                "abiertas": 1, "cerradas": 2,
            })
            self.csv("asistencias")

    def test_frecuencia_y_dias_excluyen_anuladas(self):
        resultado = self.reporte("asistencias", fecha_desde="2026-11-08", fecha_hasta="2026-11-08")
        frecuencia, diario = resultado["resumenes"]
        self.assertEqual({f["socio"]: f["asistencias"] for f in frecuencia["pagina"].filas}, {"Ana Pérez": 1, "Bruno López": 2})
        self.assertEqual(diario["pagina"].filas[0]["asistencias"], 3)
        self.assertEqual(str(diario["pagina"].filas[0]["fecha"]), "2026-11-08")
        anuladas = self.reporte("asistencias", estado="anulada")
        self.assertEqual(anuladas["pagina"].total, 1)
        self.assertEqual(anuladas["indicadores"]["total"], 0)
        self.assertEqual(anuladas["indicadores"]["socios_unicos"], 0)
        self.assertEqual(anuladas["resumenes"][0]["pagina"].filas, [])

    def test_filtros_socio_membresia_y_estado(self):
        resultado = self.reporte("asistencias", socio_id=self.datos["bruno"].id, membresia_id=self.datos["proxima"].id, estado="cerrada")
        self.assertEqual(resultado["indicadores"]["total"], 2)
        self.assertEqual(resultado["indicadores"]["socios_unicos"], 1)
        self.assertEqual(self.reporte("asistencias", socio="Nadie")["indicadores"]["total"], 0)
        self.assertEqual(self.reporte("asistencias", socio="Nadie")["pagina"].filas, [])

    def test_csv_respeta_filtros_y_muestra_salida_del_dia_siguiente(self):
        texto = self.csv("asistencias", estado="cerrada", fecha_desde="2026-11-08", fecha_hasta="2026-11-08").decode("utf-8-sig")
        filas = list(csv.DictReader(StringIO(texto), delimiter=";"))
        self.assertEqual(len(filas), 2)
        self.assertEqual({f["Estado"] for f in filas}, {"cerrada"})
        self.assertIn("2026-11-09 01:00:00", {f["Fecha y hora de salida"] for f in filas})
