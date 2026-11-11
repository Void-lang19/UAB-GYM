import unittest

from app import db
from app.models import Asistencia, Entrenador, Membresia, Pago, Plan, Socio
from app.seed_demo import cargar_datos_demo
from tests._modulos_support import app as test_app


class CargaDatosDemoTests(unittest.TestCase):
    def setUp(self):
        self.contexto = test_app.app_context()
        self.contexto.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_inserta_datos_ficticios_y_es_idempotente(self):
        primero = cargar_datos_demo()
        segundo = cargar_datos_demo()

        self.assertEqual(primero, {
            "socios": 3, "entrenadores": 2, "planes": 3,
            "membresias": 3, "pagos": 4, "asistencias": 3,
        })
        self.assertTrue(all(cantidad == 0 for cantidad in segundo.values()))
        self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Socio)), 3)
        self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Entrenador)), 2)
        self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Plan)), 3)
        self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Membresia)), 3)
        self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Pago)), 4)
        self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Asistencia)), 3)
        socios = db.session.execute(db.select(Socio)).scalars().all()
        entrenadores = db.session.execute(db.select(Entrenador)).scalars().all()
        planes = db.session.execute(db.select(Plan)).scalars().all()
        membresias = db.session.execute(db.select(Membresia)).scalars().all()
        pagos = db.session.execute(db.select(Pago)).scalars().all()
        asistencias = db.session.execute(db.select(Asistencia)).scalars().all()
        datos_visibles = [
            valor
            for registro, campos in [
                *((socio, ("documento_identidad", "nombres", "apellidos")) for socio in socios),
                *((entrenador, ("documento_identidad", "nombres", "apellidos")) for entrenador in entrenadores),
                *((plan, ("nombre", "descripcion", "beneficios")) for plan in planes),
                *((membresia, ("observaciones",)) for membresia in membresias),
                *((pago, ("referencia", "observaciones", "motivo_anulacion")) for pago in pagos),
                *((asistencia, ("observaciones",)) for asistencia in asistencias),
            ]
            for valor in (getattr(registro, campo) for campo in campos)
            if valor
        ]
        self.assertTrue(all("demo" not in valor.casefold() for valor in datos_visibles))


if __name__ == "__main__":
    unittest.main()
