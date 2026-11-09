from datetime import datetime

from flask import flash, has_request_context, redirect, request
from flask_appbuilder import ModelView, action
from flask_appbuilder.models.sqla.interface import SQLAInterface
from wtforms import SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from app import db
from app.models import Pago
from app.services import METODOS_PAGO, anular_pago, validar_pago


def validar_saldo(form, field):
    membresia = getattr(form, "membresia", None)
    metodo = getattr(form, "metodo_pago", None)
    if not membresia or not membresia.data or not metodo or not metodo.data or field.data is None:
        return
    candidato = Pago(membresia_id=membresia.data.id, monto=field.data, metodo_pago=metodo.data)
    try:
        excluir = (request.view_args or {}).get("pk") if has_request_context() else None
        validar_pago(candidato, excluir_pago_id=int(excluir) if excluir else None)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


class PagoModelView(ModelView):
    datamodel = SQLAInterface(Pago, db.session)
    route_base = "/pagos"
    can_delete = False
    exclude_route_methods = {"delete"}
    list_title = "Pagos"
    add_title = "Registrar pago"
    edit_title = "Corregir pago"
    show_title = "Información del pago"
    list_columns = ["membresia", "fecha_pago", "monto", "metodo_pago", "estado"]
    show_columns = ["membresia", "fecha_pago", "monto", "metodo_pago", "referencia", "estado", "observaciones", "fecha_anulacion", "motivo_anulacion"]
    add_columns = ["membresia", "monto", "metodo_pago", "referencia", "observaciones"]
    edit_columns = ["membresia", "monto", "metodo_pago", "referencia", "observaciones"]
    search_columns = ["membresia", "fecha_pago", "metodo_pago", "estado", "referencia"]
    label_columns = {"membresia": "Membresía", "fecha_pago": "Fecha de pago", "monto": "Monto", "metodo_pago": "Método de pago", "referencia": "Referencia", "estado": "Estado", "observaciones": "Observaciones", "fecha_anulacion": "Fecha de anulación", "motivo_anulacion": "Motivo de anulación"}
    validators_columns = {"monto": [DataRequired(), NumberRange(min=0.01), validar_saldo], "metodo_pago": [DataRequired()], "referencia": [Optional(), Length(max=120)], "observaciones": [Optional()]}
    add_form_extra_fields = {"metodo_pago": SelectField("Método de pago", choices=[(x, x) for x in METODOS_PAGO], validators=[DataRequired()])}
    edit_form_extra_fields = {"metodo_pago": SelectField("Método de pago", choices=[(x, x) for x in METODOS_PAGO], validators=[DataRequired()])}
    base_order = ("fecha_pago", "desc")

    def pre_add(self, item):
        item.fecha_pago = item.fecha_pago or datetime.utcnow()
        validar_pago(item)

    def pre_update(self, item):
        validar_pago(item, excluir_pago_id=item.id)

    @action("anular", "Anular", "¿Anular los pagos seleccionados?", "fa-ban")
    def anular(self, items):
        try:
            for pago in (items if isinstance(items, list) else [items]):
                anular_pago(pago, "Anulado por usuario autorizado")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "warning")
            return redirect(self.get_redirect())
        flash("Pagos anulados y excluidos del saldo; los registros se conservaron.", "success")
        return redirect(self.get_redirect())
