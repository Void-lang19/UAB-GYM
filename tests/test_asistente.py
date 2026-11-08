from datetime import date
import os
import unittest
from unittest.mock import Mock, patch

from app.services_asistente import (
    AsistenteNoConfigurado,
    construir_contexto,
    responder_pregunta,
)


class AsistenteTests(unittest.TestCase):
    def test_contexto_no_financiero_excluye_pagos_y_datos_personales(self):
        def reporte(tipo, **_filtros):
            return {"total": "4", "socios_unicos": "3"} if tipo == "asistencias" else {"vigentes": "2"}

        with patch("app.services_asistente._reporte", side_effect=reporte) as consultar:
            contexto = construir_contexto(administrador=False, hoy=date(2026, 11, 8))

        self.assertNotIn("pagos", contexto)
        self.assertEqual(contexto["fecha_consulta"], "2026-11-08")
        self.assertEqual(contexto["asistencias"]["mes_actual"]["total"], "4")
        self.assertEqual(consultar.call_count, 4)
        for llamada in consultar.call_args_list:
            self.assertNotIn("socio", llamada.kwargs)

    def test_contexto_admin_incluye_totales_financieros(self):
        with patch("app.services_asistente._reporte", return_value={"ingresos": "125.00"}):
            contexto = construir_contexto(administrador=True, hoy=date(2026, 11, 8))
        self.assertIn("pagos", contexto)
        self.assertEqual(contexto["pagos"]["mes_actual"]["ingresos"], "125.00")

    def test_sin_clave_muestra_error_de_configuracion(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(AsistenteNoConfigurado):
                responder_pregunta("¿Cuántas asistencias hubo?", {})

    def test_respuesta_usa_responses_api_sin_guardar_conversacion(self):
        respuesta = Mock(output_text="Hubo 12 asistencias este mes.")
        cliente = Mock()
        cliente.responses.create.return_value = respuesta
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"}),
            patch("openai.OpenAI", return_value=cliente) as construir_cliente,
        ):
            texto = responder_pregunta("¿Cuántas asistencias hubo?", {"asistencias": {"mes_actual": {"total": "12"}}})

        self.assertEqual(texto, "Hubo 12 asistencias este mes.")
        construir_cliente.assert_called_once_with(api_key="test-key", timeout=25.0, max_retries=0)
        parametros = cliente.responses.create.call_args.kwargs
        self.assertEqual(parametros["model"], "test-model")
        self.assertFalse(parametros["store"])
        self.assertIn("¿Cuántas asistencias hubo?", parametros["input"])


if __name__ == "__main__":
    unittest.main()
