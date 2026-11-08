from datetime import date, timedelta
from types import SimpleNamespace
import unittest

from wtforms.validators import Email, ValidationError

from app.views.entrenadores import (
    EntrenadorModelView,
    validate_fecha_contratacion,
)


class EntrenadorModelViewTests(unittest.TestCase):
    def test_view_exposes_trainer_search_and_crud_columns(self) -> None:
        self.assertEqual(EntrenadorModelView.route_base, "/entrenadores")
        self.assertIn("especialidad", EntrenadorModelView.list_columns)
        self.assertIn("documento_identidad", EntrenadorModelView.search_columns)
        self.assertIn("correo_electronico", EntrenadorModelView.search_columns)
        self.assertIn("fecha_contratacion", EntrenadorModelView.show_columns)

    def test_hard_delete_is_disabled_and_deactivation_is_inherited(self) -> None:
        self.assertFalse(EntrenadorModelView.can_delete)
        self.assertIn("delete", EntrenadorModelView.exclude_route_methods)
        self.assertEqual(EntrenadorModelView.desactivar._action[0], "desactivar")

    def test_validates_email_and_rejects_future_hiring_dates(self) -> None:
        email_validator = next(
            validator
            for validator in EntrenadorModelView.validators_columns[
                "correo_electronico"
            ]
            if isinstance(validator, Email)
        )
        email_field = SimpleNamespace(
            data="correo-invalido",
            gettext=lambda message: message,
        )
        with self.assertRaises(ValidationError):
            email_validator(None, email_field)

        with self.assertRaises(ValidationError):
            validate_fecha_contratacion(
                None,
                SimpleNamespace(data=date.today() + timedelta(days=1)),
            )
        validate_fecha_contratacion(
            None,
            SimpleNamespace(data=date.today() - timedelta(days=1)),
        )


if __name__ == "__main__":
    unittest.main()
