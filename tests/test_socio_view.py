from datetime import date, timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from wtforms.validators import Email, ValidationError

from app.views.socios import SocioModelView, validate_fecha_nacimiento


class SocioModelViewTests(unittest.TestCase):
    def test_view_exposes_member_search_and_crud_columns(self) -> None:
        self.assertEqual(SocioModelView.route_base, "/socios")
        self.assertIn("documento_identidad", SocioModelView.search_columns)
        self.assertIn("correo_electronico", SocioModelView.search_columns)
        self.assertIn("fecha_nacimiento", SocioModelView.show_columns)
        self.assertIn("direccion", SocioModelView.add_columns)

    def test_hard_delete_is_disabled_and_deactivation_is_available(self) -> None:
        self.assertFalse(SocioModelView.can_delete)
        self.assertIn("delete", SocioModelView.exclude_route_methods)
        self.assertEqual(SocioModelView.desactivar._action[0], "desactivar")

    def test_form_validates_email_and_rejects_future_birth_dates(self) -> None:
        validators = SocioModelView.validators_columns
        email_validator = next(
            validator
            for validator in validators["correo_electronico"]
            if isinstance(validator, Email)
        )
        email_field = SimpleNamespace(
            data="correo-invalido",
            gettext=lambda message: message,
        )
        with self.assertRaises(ValidationError):
            email_validator(None, email_field)

        with self.assertRaises(ValidationError):
            validate_fecha_nacimiento(
                None,
                SimpleNamespace(data=date.today() + timedelta(days=1)),
            )
        validate_fecha_nacimiento(
            None,
            SimpleNamespace(data=date.today() - timedelta(days=1)),
        )

    def test_deactivation_preserves_records_and_commits_state_change(self) -> None:
        socio = SimpleNamespace(estado="activo")
        view = SimpleNamespace(
            datamodel=SimpleNamespace(
                edit=Mock(),
                session=SimpleNamespace(commit=Mock(), rollback=Mock()),
            ),
            get_redirect=Mock(return_value="/socios/list/"),
        )
        with (
            patch("app.views.socios.flash") as flash,
            patch("app.views.socios.redirect", return_value="/socios/list/"),
        ):
            result = SocioModelView.desactivar(view, [socio])

        self.assertEqual(socio.estado, "inactivo")
        view.datamodel.edit.assert_called_once_with(socio, commit=False)
        view.datamodel.session.commit.assert_called_once()
        view.datamodel.session.rollback.assert_not_called()
        flash.assert_called_once()
        self.assertEqual(result, "/socios/list/")


if __name__ == "__main__":
    unittest.main()
