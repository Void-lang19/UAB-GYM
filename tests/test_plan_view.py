from types import SimpleNamespace
import unittest

from wtforms.validators import NumberRange, ValidationError

from app.views.planes import PlanModelView


class PlanModelViewTests(unittest.TestCase):
    def test_view_exposes_plan_fields_and_search(self) -> None:
        self.assertEqual(PlanModelView.route_base, "/planes")
        self.assertIn("duracion_dias", PlanModelView.list_columns)
        self.assertIn("precio", PlanModelView.show_columns)
        self.assertIn("beneficios", PlanModelView.add_columns)
        self.assertIn("nombre", PlanModelView.search_columns)

    def test_hard_delete_is_disabled_and_deactivation_is_inherited(self) -> None:
        self.assertFalse(PlanModelView.can_delete)
        self.assertIn("delete", PlanModelView.exclude_route_methods)
        self.assertEqual(PlanModelView.desactivar._action[0], "desactivar")

    def test_validates_positive_duration_and_non_negative_price(self) -> None:
        validators = PlanModelView.validators_columns
        duration_validator = next(
            validator
            for validator in validators["duracion_dias"]
            if isinstance(validator, NumberRange)
        )
        price_validator = next(
            validator
            for validator in validators["precio"]
            if isinstance(validator, NumberRange)
        )

        def make_field(value: float | int) -> SimpleNamespace:
            return SimpleNamespace(
                data=value,
                gettext=lambda message: message,
            )

        with self.assertRaises(ValidationError):
            duration_validator(None, make_field(0))
        duration_validator(None, make_field(1))

        with self.assertRaises(ValidationError):
            price_validator(None, make_field(-0.01))
        price_validator(None, make_field(0))


if __name__ == "__main__":
    unittest.main()
