from flask_appbuilder.models.sqla.interface import SQLAInterface
from wtforms import SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app import db
from app.models import Plan
from app.views.base import ESTADO_CHOICES, SoftDeactivateModelView


class PlanModelView(SoftDeactivateModelView):
    datamodel = SQLAInterface(Plan, db.session)
    route_base = "/planes"
    entity_plural = "planes"
    list_title = "Planes"
    add_title = "Registrar plan"
    edit_title = "Editar plan"
    show_title = "Información del plan"
    base_order = ("nombre", "asc")

    list_columns = ["nombre", "duracion_dias", "precio", "estado"]
    show_columns = [
        "nombre",
        "descripcion",
        "duracion_dias",
        "precio",
        "beneficios",
        "estado",
    ]
    add_columns = show_columns
    edit_columns = show_columns
    search_columns = ["nombre", "descripcion", "estado"]

    label_columns = {
        "nombre": "Nombre",
        "descripcion": "Descripción",
        "duracion_dias": "Duración (días)",
        "precio": "Precio",
        "beneficios": "Beneficios",
        "estado": "Estado",
    }

    validators_columns = {
        "nombre": [DataRequired(), Length(max=100)],
        "descripcion": [Optional()],
        "duracion_dias": [DataRequired(), NumberRange(min=1)],
        "precio": [DataRequired(), NumberRange(min=0)],
        "beneficios": [Optional()],
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
