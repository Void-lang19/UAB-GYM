from datetime import date
from decimal import Decimal
import unittest

from app import db
from app.models import Membresia, Pago
from app.services import anular_pago, preparar_membresia, total_pagado, validar_pago
from app.views.pagos import PagoModelView
from tests._modulos_support import app, limpiar_base, crear_datos_basicos


class PagoServiceTests(unittest.TestCase):
    def test_view_disables_physical_deletion(self):
        self.assertFalse(PagoModelView.can_delete)
        self.assertIn("delete", PagoModelView.exclude_route_methods)

    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        limpiar_base()
        socio, plan = crear_datos_basicos()
        self.membresia = Membresia(socio_id=socio.id, plan_id=plan.id, fecha_inicio=date.today())
        preparar_membresia(self.membresia)
        db.session.add(self.membresia)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.context.pop()

    def test_acepta_parciales_y_rechaza_sobrepago(self):
        for importe in ("100.00", "50.00"):
            pago = Pago(membresia_id=self.membresia.id, monto=Decimal(importe), metodo_pago="Efectivo")
            validar_pago(pago)
            db.session.add(pago)
            db.session.commit()
        self.assertEqual(total_pagado(self.membresia.id), Decimal("150.00"))
        with self.assertRaisesRegex(ValueError, "supera"):
            validar_pago(Pago(membresia_id=self.membresia.id, monto=Decimal("50.01"), metodo_pago="QR"))

    def test_valida_pago_con_membresia_asignada_por_el_formulario(self):
        pago = Pago(membresia=self.membresia, monto=Decimal("50.00"), metodo_pago="QR")

        validar_pago(pago)

        self.assertEqual(pago.membresia_id, self.membresia.id)

    def test_anulacion_conserva_pago_y_lo_excluye_del_total(self):
        pago = Pago(membresia_id=self.membresia.id, monto=Decimal("75.00"), metodo_pago="QR")
        validar_pago(pago)
        db.session.add(pago)
        db.session.commit()
        anular_pago(pago, "Duplicado")
        self.assertEqual(pago.estado, "anulado")
        self.assertEqual(total_pagado(self.membresia.id), Decimal("0.00"))
        self.assertEqual(pago.motivo_anulacion, "Duplicado")


if __name__ == "__main__":
    unittest.main()
