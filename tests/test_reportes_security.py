import codecs
import unittest
from unittest.mock import patch

from flask_appbuilder import AppBuilder
from flask_appbuilder.security.manager import AUTH_DB
from sqlalchemy.exc import SQLAlchemyError

import app as app_module
from app import db
from app.security import configure_application_roles
from tests._reportes_support import sembrar_reportes


def permisos(rol):
    return {(p.permission.name, p.view_menu.name) for p in rol.permissions}


class ReportesSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configuracion = {
            "SECRET_KEY": "reportes-test-" + "x" * 48,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "AUTH_TYPE": AUTH_DB, "AUTH_ROLE_ADMIN": "Admin",
            "AUTH_USER_REGISTRATION": False, "WTF_CSRF_ENABLED": False, "TESTING": True,
        }
        # La fábrica actual usa un AppBuilder global. Aislarlo evita que las
        # pruebas de reportes compartan registro de vistas con otras suites.
        with (
            patch.object(app_module, "load_config", return_value=configuracion),
            patch.object(app_module, "appbuilder", AppBuilder()),
        ):
            cls.app = app_module.create_app()
            cls.sm = app_module.appbuilder.sm
        with cls.app.app_context():
            db.create_all()
            cls.admin_antes = permisos(cls.sm.find_role("Admin"))
            cls.public_antes = permisos(cls.sm.find_role("Public"))
            configure_application_roles(cls.sm)
            sembrar_reportes()
            for nombre in ("Admin", "Recepcionista", "Entrenador"):
                usuario = cls.sm.add_user(
                    "reportes-" + nombre, "Prueba", nombre,
                    nombre.lower() + "@example.test", cls.sm.find_role(nombre),
                    password="solo-pruebas-reportes",
                )
                if usuario is None:
                    raise RuntimeError("No se pudo crear el usuario de prueba.")

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def cliente(self, rol=None):
        cliente = self.app.test_client()
        if rol:
            respuesta = cliente.post("/login/", data={
                "username": "reportes-" + rol, "password": "solo-pruebas-reportes",
            })
            self.assertEqual(respuesta.status_code, 302)
        return cliente

    def assert_denegado(self, respuesta):
        # FAB puede redirigir al login o responder 401/403 según su versión.
        self.assertIn(respuesta.status_code, (302, 401, 403))
        self.assertNotIn("text/csv", respuesta.content_type)
        self.assertNotIn(b"PRUEBA-ANA", respuesta.data)
        if respuesta.status_code == 302:
            self.assertIn("/login/", respuesta.headers["Location"])

    def test_admin_accede_a_tres_pantallas_y_tres_exportaciones(self):
        cliente = self.cliente("Admin")
        for tipo in ("membresias", "pagos", "asistencias"):
            with self.subTest(tipo=tipo):
                respuesta = cliente.get(f"/reportes/{tipo}/")
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn("no-store", respuesta.headers["Cache-Control"])
                respuesta = cliente.get(f"/reportes/{tipo}/exportar.csv")
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.data.startswith(codecs.BOM_UTF8))
                self.assertIn("attachment", respuesta.headers["Content-Disposition"])
                self.assertNotIn(b"PRUEBA-ANA", respuesta.data)
                respuesta.close()

    def test_recepcionista_solo_membresias_y_asistencias(self):
        cliente = self.cliente("Recepcionista")
        for tipo in ("membresias", "asistencias"):
            for sufijo in ("", "exportar.csv"):
                respuesta = cliente.get(f"/reportes/{tipo}/{sufijo}")
                self.assertEqual(respuesta.status_code, 200)
                respuesta.close()
        for sufijo in ("", "exportar.csv"):
            self.assert_denegado(cliente.get(f"/reportes/pagos/{sufijo}"))

    def test_entrenador_y_anonimos_no_pueden_consultar_por_url(self):
        for rol in (None, "Entrenador"):
            cliente = self.cliente(rol)
            for tipo in ("membresias", "pagos", "asistencias"):
                for sufijo in ("", "exportar.csv"):
                    with self.subTest(rol=rol, tipo=tipo, sufijo=sufijo):
                        self.assert_denegado(cliente.get(f"/reportes/{tipo}/{sufijo}"))

    def test_exportacion_y_pantalla_comparten_permiso(self):
        with self.app.app_context():
            rol = self.sm.find_role("Recepcionista")
            permiso = self.sm.find_permission_view_menu("can_consultar", "ReporteMembresiasView")
            self.sm.del_permission_role(rol, permiso)
        try:
            cliente = self.cliente("Recepcionista")
            self.assert_denegado(cliente.get("/reportes/membresias/"))
            self.assert_denegado(cliente.get("/reportes/membresias/exportar.csv"))
        finally:
            with self.app.app_context():
                permiso = self.sm.find_permission_view_menu("can_consultar", "ReporteMembresiasView")
                self.sm.add_permission_role(self.sm.find_role("Recepcionista"), permiso)

    def test_reportes_solo_get_y_validacion_igual_en_csv(self):
        cliente = self.cliente("Admin")
        for tipo in ("membresias", "pagos", "asistencias"):
            for sufijo in ("", "exportar.csv"):
                ruta = f"/reportes/{tipo}/{sufijo}"
                self.assertEqual(cliente.post(ruta).status_code, 405)
                self.assertEqual(cliente.get(ruta + "?pagina=-1").status_code, 400)
                self.assertEqual(cliente.get(ruta + "?estado=inexistente").status_code, 400)

    def test_vacio_error_tecnico_y_filtros_en_enlace_csv(self):
        cliente = self.cliente("Admin")
        vacio = cliente.get("/reportes/membresias/?socio=Nadie")
        self.assertEqual(vacio.status_code, 200)
        self.assertIn(b"No se encontraron registros para los filtros seleccionados", vacio.data)
        pagina = cliente.get("/reportes/membresias/?estado=vigente&fecha_referencia=2026-11-08&por_pagina=10")
        self.assertIn(b"exportar.csv?", pagina.data)
        self.assertIn(b"estado=vigente", pagina.data)
        self.assertIn(b"fecha_referencia=2026-11-08", pagina.data)
        with patch("app.views.reportes.obtener_reporte", side_effect=SQLAlchemyError("SECRETO-DB")):
            error = cliente.get("/reportes/membresias/")
        self.assertEqual(error.status_code, 500)
        self.assertNotIn(b"SECRETO-DB", error.data)
        with patch("app.views.reportes.crear_archivo_csv", side_effect=OSError("SECRETO-RUTA")):
            error = cliente.get("/reportes/membresias/exportar.csv")
        self.assertEqual(error.status_code, 500)
        self.assertNotIn(b"SECRETO-RUTA", error.data)

    def test_busqueda_html_escapada(self):
        respuesta = self.cliente("Admin").get("/reportes/membresias/", query_string={"socio": "<script>alert(1)</script>"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn(b"<script>alert(1)</script>", respuesta.data)
        self.assertIn(b"&lt;script&gt;", respuesta.data)

    def test_permisos_previos_admin_public_y_reconciliacion(self):
        with self.app.app_context():
            configure_application_roles(self.sm)
            self.assertEqual(permisos(self.sm.find_role("Admin")), self.admin_antes)
            self.assertEqual(permisos(self.sm.find_role("Public")), self.public_antes)
            recepcion = permisos(self.sm.find_role("Recepcionista"))
            entrenador = permisos(self.sm.find_role("Entrenador"))
            self.assertIn(("can_add", "PagoModelView"), recepcion)
            self.assertIn(("registrar_salida", "AsistenciaModelView"), recepcion)
            self.assertIn(("can_edit", "MembresiaModelView"), recepcion)
            self.assertNotIn(("can_edit", "PagoModelView"), recepcion)
            self.assertNotIn(("can_consultar", "ReportePagosView"), recepcion)
            self.assertIn(("can_list", "PlanModelView"), entrenador)
            self.assertFalse(any(v.startswith("Reporte") for _, v in entrenador))
