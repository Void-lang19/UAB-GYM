from flask import flash, has_request_context, redirect, request
from flask_appbuilder import action
from flask_appbuilder.models.sqla.interface import SQLAInterface
from wtforms import DateField, Form
from wtforms.validators import DataRequired, Optional, ValidationError

from app import db
from app.models import Membresia
from app.services import cancelar_membresia, preparar_membresia, renovar_membresia
from app.views.base import SoftDeactivateModelView


def validar_inicio(_form: Form, field: DateField) -> None:
    if not field.data:
        raise ValidationError("La fecha de inicio es obligatoria.")


def validar_reglas_contratacion(form: Form, field: DateField) -> None:
    if not field.data:
        return
    socio = getattr(form, "socio", None)
    plan = getattr(form, "plan", None)
    if not socio or not socio.data or not plan or not plan.data:
        return
    candidato = Membresia(
        socio_id=socio.data.id,
        plan_id=plan.data.id,
        fecha_inicio=field.data,
        estado=getattr(getattr(form, "estado", None), "data", None) or "activa",
    )
    try:
        excluir = (request.view_args or {}).get("pk") if has_request_context() else None
        preparar_membresia(candidato, excluir_id=int(excluir) if excluir else None)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


class MembresiaModelView(SoftDeactivateModelView):
    datamodel = SQLAInterface(Membresia, db.session)
    route_base = "/membresias"
    entity_plural = "membresías"
    estado_inactivo = "cancelada"
    can_delete = False
    exclude_route_methods = {"delete"}
    list_columns = ["socio", "plan", "fecha_inicio", "fecha_fin", "precio_pactado", "estado", "vigencia"]
    show_columns = ["socio", "plan", "fecha_inicio", "fecha_fin", "precio_pactado", "estado", "vigencia", "fecha_registro", "observaciones", "fecha_cancelacion", "motivo_cancelacion"]
    add_columns = ["socio", "plan", "fecha_inicio", "observaciones"]
    edit_columns = ["socio", "plan", "fecha_inicio", "observaciones", "estado"]
    # Flask-AppBuilder builds search fields from database columns; ``vigencia``
    # is a hybrid display property and is not searchable through its converter.
    search_columns = ["socio", "plan", "estado", "fecha_inicio", "fecha_fin"]
    label_columns = {"socio": "Socio", "plan": "Plan", "fecha_inicio": "Inicio", "fecha_fin": "Vencimiento", "precio_pactado": "Precio pactado", "estado": "Estado administrativo", "vigencia": "Vigencia", "fecha_registro": "Registrada", "observaciones": "Observaciones"}
    validators_columns = {"fecha_inicio": [DataRequired(), validar_inicio, validar_reglas_contratacion], "observaciones": [Optional()]}
    add_form_extra_fields = {"fecha_inicio": DateField("Fecha de inicio", validators=[DataRequired(), validar_inicio, validar_reglas_contratacion])}
    edit_form_extra_fields = {"fecha_inicio": DateField("Fecha de inicio", validators=[DataRequired(), validar_inicio, validar_reglas_contratacion])}
    add_exclude_columns = ["fecha_fin", "precio_pactado", "estado", "fecha_registro"]
    base_order = ("fecha_inicio", "desc")

    def pre_add(self, item):
        preparar_membresia(item)

    def pre_update(self, item):
        preparar_membresia(item, excluir_id=item.id)

    @action("desactivar", "Cancelar", "¿Cancelar las membresías seleccionadas? Se conservará el historial.", "fa-ban")
    def desactivar(self, items):
        try:
            for item in (items if isinstance(items, list) else [items]):
                cancelar_membresia(item)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "warning")
            return redirect(self.get_redirect())
        flash("Membresías canceladas; el historial se conservó.", "success")
        return redirect(self.get_redirect())

    @action("renovar", "Renovar", "¿Crear una nueva membresía a partir de la selección?", "fa-refresh")
    def renovar(self, items):
        try:
            for item in (items if isinstance(items, list) else [items]):
                renovar_membresia(item)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "warning")
            return redirect(self.get_redirect())
        flash("Se creó una nueva membresía para cada socio seleccionado.", "success")
        return redirect(self.get_redirect())
