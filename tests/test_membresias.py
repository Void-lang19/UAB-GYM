from datetime import date, timedelta
from decimal import Decimal
import unittest

from app import db
from app.models import Membresia
from app.services import preparar_membresia, renovar_membresia
from app.views.membresias import MembresiaModelView
from tests._modulos_support import app, limpiar_base, crear_datos_basicos


class MembresiaServiceTests(unittest.TestCase):
    def test_view_disables_physical_deletion_and_exposes_expected_fields(self):
        self.assertFalse(MembresiaModelView.can_delete)
        self.assertIn("delete", MembresiaModelView.exclude_route_methods)
        self.assertIn("vigencia", MembresiaModelView.list_columns)
        self.assertIn("fecha_inicio", MembresiaModelView.search_columns)

    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        limpiar_base()
        self.socio, self.plan = crear_datos_basicos()

    def tearDown(self):
        db.session.remove()
        self.context.pop()

    def test_calcula_vencimiento_y_conserva_precio_contratado(self):
        membresia = Membresia(socio_id=self.socio.id, plan_id=self.plan.id, fecha_inicio=date(2026, 11, 1))
        preparar_membresia(membresia)
        db.session.add(membresia)
        db.session.commit()
        self.plan.precio = Decimal("250.00")
        db.session.commit()
        preparar_membresia(membresia, excluir_id=membresia.id)
        self.assertEqual(membresia.fecha_fin, date(2026, 11, 30))
        self.assertEqual(membresia.precio_pactado, Decimal("200.00"))

    def test_prepara_membresia_con_relaciones_asignadas_por_el_formulario(self):
        membresia = Membresia(
            socio=self.socio,
            plan=self.plan,
            fecha_inicio=date.today(),
        )

        preparar_membresia(membresia)

        self.assertEqual(membresia.socio_id, self.socio.id)
        self.assertEqual(membresia.plan_id, self.plan.id)
        self.assertEqual(membresia.precio_pactado, self.plan.precio)

    def test_rechaza_socios_inactivos_y_periodos_superpuestos(self):
        existente = Membresia(socio_id=self.socio.id, plan_id=self.plan.id, fecha_inicio=date.today())
        preparar_membresia(existente)
        db.session.add(existente)
        db.session.commit()
        superpuesta = Membresia(socio_id=self.socio.id, plan_id=self.plan.id, fecha_inicio=date.today() + timedelta(days=2))
        with self.assertRaisesRegex(ValueError, "período"):
            preparar_membresia(superpuesta)
        self.socio.estado = "inactivo"
        with self.assertRaisesRegex(ValueError, "inactivos"):
            preparar_membresia(Membresia(socio_id=self.socio.id, plan_id=self.plan.id, fecha_inicio=date.today() + timedelta(days=31)))

    def test_renovacion_crea_registro_nuevo(self):
        antigua = Membresia(socio_id=self.socio.id, plan_id=self.plan.id, fecha_inicio=date.today() - timedelta(days=30))
        preparar_membresia(antigua)
        db.session.add(antigua)
        db.session.commit()
        nueva = renovar_membresia(antigua)
        self.assertNotEqual(antigua.id, nueva.id)
        self.assertEqual(nueva.fecha_inicio, antigua.fecha_fin + timedelta(days=1))


if __name__ == "__main__":
    unittest.main()
