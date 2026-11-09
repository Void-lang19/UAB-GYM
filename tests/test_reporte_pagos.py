import csv
from decimal import Decimal
from io import StringIO

from app.services import total_pagado
from tests._reportes_support import ReporteDatosTest


class ReportePagosTests(ReporteDatosTest):
    def test_parciales_anulados_y_limites_de_dias_locales_en_utc(self):
        with self.solo_lectura():
            resultado = self.reporte("pagos", fecha_desde="2026-11-08", fecha_hasta="2026-11-08")
            indicadores = resultado["indicadores"]
            self.assertEqual(indicadores["ingresos"], Decimal("162.35"))
            self.assertIsInstance(indicadores["ingresos"], Decimal)
            self.assertEqual(indicadores["cantidad_pagos"], 3)
            self.assertEqual(indicadores["anulados"], 1)
            self.assertEqual(resultado["pagina"].total, 4)
            self.assertEqual({f["fecha_pago"].date().isoformat() for f in resultado["pagina"].filas}, {"2026-11-08"})
            self.csv("pagos", fecha_desde="2026-11-08", fecha_hasta="2026-11-08")

    def test_agrupaciones_no_duplican_importes_y_cancelada_conserva_ingresos(self):
        resultado = self.reporte("pagos", fecha_desde="2026-11-08", fecha_hasta="2026-11-08")
        for resumen in resultado["resumenes"]:
            self.assertEqual(sum((f["ingresos"] for f in resumen["pagina"].filas), Decimal("0")), Decimal("162.35"))
        planes = {f["plan"]: f["ingresos"] for f in resultado["resumenes"][1]["pagina"].filas}
        self.assertEqual(planes[self.datos["semanal"].nombre], Decimal("12.10"))
        self.assertEqual(self.reporte("pagos", metodo_pago="QR")["indicadores"]["ingresos"], Decimal("50.25"))
        self.assertEqual(self.reporte("pagos", estado="anulado")["indicadores"]["ingresos"], Decimal("0.00"))

    def test_saldo_actual_incluye_sin_pagos_y_usa_precio_historico(self):
        esperado = sum((m.precio_pactado - total_pagado(m.id) for k, m in self.datos.items()
                        if k in {"vigente", "proxima", "vencida", "programada", "cancelada"}), Decimal("0"))
        resultado = self.reporte("pagos", fecha_desde="2026-11-08", fecha_hasta="2026-11-08", metodo_pago="QR")
        self.assertEqual(resultado["indicadores"]["saldo"], esperado)
        self.assertEqual(esperado, Decimal("522.65"))
        self.assertEqual(resultado["indicadores"]["membresias_saldo"], 5)
        por_socio = self.reporte("pagos", socio="Bruno", plan_id=self.datos["mensual"].id)
        self.assertEqual(por_socio["indicadores"]["ingresos"], Decimal("0.00"))
        self.assertEqual(por_socio["indicadores"]["saldo"], Decimal("200.00"))

    def test_csv_precision_filtros_y_resultados_vacios(self):
        contenido = self.csv("pagos", metodo_pago="QR", estado="valido")
        filas = list(csv.DictReader(StringIO(contenido.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["Monto"], "50.25")
        self.assertEqual(filas[0]["Método"], "QR")
        vacio = self.reporte("pagos", socio="Sin coincidencias")
        self.assertEqual(vacio["indicadores"]["ingresos"], Decimal("0.00"))
        self.assertEqual(vacio["indicadores"]["saldo"], Decimal("0.00"))
        self.assertEqual(vacio["pagina"].filas, [])
