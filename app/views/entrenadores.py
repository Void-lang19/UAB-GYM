from datetime import date

from flask_appbuilder.models.sqla.interface import SQLAInterface
from wtforms import DateField, Form, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app import db
from app.models import Entrenador
from app.views.base import ESTADO_CHOICES, SoftDeactivateModelView


def validate_fecha_contratacion(_form: Form, field: DateField) -> None:
    if field.data and field.data > date.today():
        raise ValidationError("La fecha de contratación no puede ser futura.")


class EntrenadorModelView(SoftDeactivateModelView):
    datamodel = SQLAInterface(Entrenador, db.session)
    route_base = "/entrenadores"
    entity_plural = "entrenadores"
    list_title = "Entrenadores"
    add_title = "Registrar entrenador"
    edit_title = "Editar entrenador"
    show_title = "Información del entrenador"
    base_order = ("apellidos", "asc")

    list_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "telefono",
        "especialidad",
        "estado",
    ]
    show_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "telefono",
        "correo_electronico",
        "especialidad",
        "fecha_contratacion",
        "estado",
    ]
    add_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "telefono",
        "correo_electronico",
        "especialidad",
        "fecha_contratacion",
        "estado",
    ]
    edit_columns = add_columns
    search_columns = [
        "nombres",
        "apellidos",
        "documento_identidad",
        "correo_electronico",
        "especialidad",
        "estado",
    ]

    label_columns = {
        "nombres": "Nombres",
        "apellidos": "Apellidos",
        "documento_identidad": "Documento de identidad",
        "telefono": "Teléfono",
        "correo_electronico": "Correo electrónico",
        "especialidad": "Especialidad",
        "fecha_contratacion": "Fecha de contratación",
        "estado": "Estado",
    }

    validators_columns = {
        "nombres": [DataRequired(), Length(max=100)],
        "apellidos": [DataRequired(), Length(max=100)],
        "documento_identidad": [DataRequired(), Length(max=30)],
        "telefono": [Optional(), Length(max=25)],
        "correo_electronico": [Optional(), Email(), Length(max=254)],
        "especialidad": [DataRequired(), Length(max=120)],
        "fecha_contratacion": [DataRequired(), validate_fecha_contratacion],
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
