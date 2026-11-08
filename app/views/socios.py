from datetime import date

from flask_appbuilder.models.sqla.interface import SQLAInterface
from wtforms import DateField, Form, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app import db
from app.models import Socio
from app.views.base import ESTADO_CHOICES, SoftDeactivateModelView


def validate_fecha_nacimiento(_form: Form, field: DateField) -> None:
    if field.data and field.data > date.today():
        raise ValidationError("La fecha de nacimiento no puede ser futura.")


class SocioModelView(SoftDeactivateModelView):
    datamodel = SQLAInterface(Socio, db.session)
    route_base = "/socios"
    entity_plural = "socios"
    list_title = "Socios"
    add_title = "Registrar socio"
    edit_title = "Editar socio"
    show_title = "Información del socio"
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
    add_form_extra_fields = {
        "estado": SelectField(
            "Estado",
            choices=ESTADO_CHOICES,
            default="activo",
            validators=[DataRequired()],
        )
    }
    edit_form_extra_fields = {
        "estado": SelectField(
            "Estado",
            choices=ESTADO_CHOICES,
            validators=[DataRequired()],
        )
    }
