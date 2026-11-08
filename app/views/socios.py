import logging
from datetime import date

from flask import Response, flash, redirect
from flask_appbuilder import ModelView, action
from flask_appbuilder.models.sqla.interface import SQLAInterface
from sqlalchemy.exc import SQLAlchemyError
from wtforms import DateField, Form, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app import db
from app.models import Socio

logger = logging.getLogger(__name__)


def validate_fecha_nacimiento(_form: Form, field: DateField) -> None:
    if field.data and field.data > date.today():
        raise ValidationError("La fecha de nacimiento no puede ser futura.")


class SocioModelView(ModelView):
    datamodel = SQLAInterface(Socio, db.session)
    route_base = "/socios"
    list_title = "Socios"
    add_title = "Registrar socio"
    edit_title = "Editar socio"
    show_title = "Información del socio"
    can_delete = False
    exclude_route_methods = {"delete"}
    base_order = ("apellidos", "asc")

    list_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "telefono",
        "correo_electronico",
        "estado",
    ]
    show_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "telefono",
        "correo_electronico",
        "fecha_nacimiento",
        "direccion",
        "fecha_registro",
        "estado",
    ]
    add_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "telefono",
        "correo_electronico",
        "fecha_nacimiento",
        "direccion",
        "estado",
    ]
    edit_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "telefono",
        "correo_electronico",
        "fecha_nacimiento",
        "direccion",
        "estado",
    ]
    search_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "correo_electronico",
        "estado",
    ]

    label_columns = {
        "nombres": "Nombres",
        "apellidos": "Apellidos",
        "documento_identidad": "Documento de identidad",
        "telefono": "Teléfono",
        "correo_electronico": "Correo electrónico",
        "fecha_nacimiento": "Fecha de nacimiento",
        "direccion": "Dirección",
        "fecha_registro": "Fecha de registro",
        "estado": "Estado",
    }

    validators_columns = {
        "nombres": [DataRequired(), Length(max=100)],
        "apellidos": [DataRequired(), Length(max=100)],
        "documento_identidad": [DataRequired(), Length(max=30)],
        "telefono": [Optional(), Length(max=25)],
        "correo_electronico": [Optional(), Email(), Length(max=254)],
        "fecha_nacimiento": [Optional(), validate_fecha_nacimiento],
        "direccion": [Optional(), Length(max=255)],
    }
    _estados = [("activo", "Activo"), ("inactivo", "Inactivo")]
    add_form_extra_fields = {
        "estado": SelectField(
            "Estado",
            choices=_estados,
            default="activo",
            validators=[DataRequired()],
        )
    }
    edit_form_extra_fields = {
        "estado": SelectField(
            "Estado",
            choices=_estados,
            validators=[DataRequired()],
        )
    }

    @action(
        "desactivar",
        "Desactivar",
        "¿Desactivar los socios seleccionados? Sus datos se conservarán.",
        "fa-user-slash",
    )
    def desactivar(self, items: Socio | list[Socio]) -> Response:
        socios = items if isinstance(items, list) else [items]
        activos = [socio for socio in socios if socio.estado != "inactivo"]
        if not activos:
            flash("Los socios seleccionados ya están inactivos.", "info")
            return redirect(self.get_redirect())

        try:
            for socio in activos:
                socio.estado = "inactivo"
                self.datamodel.edit(socio, commit=False)
            self.datamodel.session.commit()
        except SQLAlchemyError:
            self.datamodel.session.rollback()
            logger.exception("No se pudieron desactivar los socios seleccionados.")
            flash(
                "No se pudieron desactivar los socios. Inténtalo nuevamente.",
                "danger",
            )
            return redirect(self.get_redirect())

        flash(f"Se desactivaron {len(activos)} socio(s).", "success")
        return redirect(self.get_redirect())
