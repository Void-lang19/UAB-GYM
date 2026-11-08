import unittest

from app.models import Entrenador, Plan, Socio


class DatabaseModelTests(unittest.TestCase):
    def test_tables_have_expected_names_and_primary_keys(self) -> None:
        expected_tables = {
            Socio: "socios",
            Entrenador: "entrenadores",
            Plan: "planes",
        }
        for model, table_name in expected_tables.items():
            with self.subTest(model=table_name):
                self.assertEqual(model.__tablename__, table_name)
                self.assertTrue(model.__table__.c.id.primary_key)

    def test_member_and_trainer_identifiers_are_required_and_unique(self) -> None:
        for model in (Socio, Entrenador):
            with self.subTest(model=model.__tablename__):
                document = model.__table__.c.documento_identidad
                email = model.__table__.c.correo_electronico
                self.assertFalse(document.nullable)
                self.assertTrue(email.nullable)
                unique_constraints = {
                    constraint.name
                    for constraint in model.__table__.constraints
                }
                self.assertIn(
                    f"uq_{model.__tablename__}_documento",
                    unique_constraints,
                )
                self.assertIn(
                    f"uq_{model.__tablename__}_correo",
                    unique_constraints,
                )

    def test_plan_has_positive_duration_and_non_negative_price_constraints(
        self,
    ) -> None:
        constraint_names = {
            constraint.name for constraint in Plan.__table__.constraints
        }
        self.assertIn("ck_planes_duracion_positiva", constraint_names)
        self.assertIn("ck_planes_precio_no_negativo", constraint_names)
        self.assertEqual(Plan.__table__.c.precio.type.precision, 10)
        self.assertEqual(Plan.__table__.c.precio.type.scale, 2)


if __name__ == "__main__":
    unittest.main()
