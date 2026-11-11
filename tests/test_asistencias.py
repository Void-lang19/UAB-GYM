from datetime import date, datetime, timedelta
import unittest

from app import db
from app.models import Asistencia, Membresia
from app.services import preparar_membresia, registrar_entrada, registrar_salida, validar_asistencia
from app.views.asistencias import AsistenciaModelView
from tests._modulos_support import app, limpiar_base, crear_datos_basicos


class AsistenciaServiceTests(unittest.TestCase):
    def test_view_disables_physical_deletion(self):
        self.assertFalse(AsistenciaModelView.can_delete)
        self.assertIn("delete", AsistenciaModelView.exclude_route_methods)

    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        limpiar_base()
        self.socio, plan = crear_datos_basicos()
        self.membresia = Membresia(socio_id=self.socio.id, plan_id=plan.id, fecha_inicio=date.today())
        preparar_membresia(self.membresia)
        db.session.add(self.membresia)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.context.pop()

    def test_registra_entrada_y_salida_y_evitar_duplicar_entrada(self):
        entrada = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=10)
        asistencia = registrar_entrada(self.socio.id, cuando=entrada)
        with self.assertRaisesRegex(ValueError, "abierta"):
            registrar_entrada(self.socio.id, cuando=entrada + timedelta(minutes=1))
        registrar_salida(asistencia, cuando=entrada + timedelta(hours=1))
        self.assertEqual(asistencia.fecha_hora_salida, entrada + timedelta(hours=1))

    def test_rechaza_sin_membresia_vigente(self):
        self.membresia.estado = "cancelada"
        db.session.commit()
        with self.assertRaisesRegex(ValueError, "no tiene una membresía vigente"):
            registrar_entrada(self.socio.id)

    def test_valida_asistencia_con_relaciones_asignadas_por_el_formulario(self):
        entrada = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=10)
        asistencia = Asistencia(
            socio=self.socio,
            membresia=self.membresia,
            fecha_hora_entrada=entrada,
        )

        validar_asistencia(asistencia)

        self.assertEqual(asistencia.socio_id, self.socio.id)
        self.assertEqual(asistencia.membresia_id, self.membresia.id)


if __name__ == "__main__":
    unittest.main()
