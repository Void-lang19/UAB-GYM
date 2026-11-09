from flask import flash, has_request_context, redirect, request
from flask_appbuilder import ModelView, action
from flask_appbuilder.models.sqla.interface import SQLAInterface
from wtforms import DateTimeField
from wtforms.validators import Optional, ValidationError

from app import db
from app.models import Asistencia
from app.services import hora_local, registrar_salida, validar_asistencia


def validar_reglas_asistencia(form, field):
    socio = getattr(form, "socio", None)
    membresia = getattr(form, "membresia", None)
    if not socio or not socio.data or not membresia or not membresia.data:
        return
    entrada = getattr(getattr(form, "fecha_hora_entrada", None), "data", None)
    candidato = Asistencia(
        socio_id=socio.data.id,
        membresia_id=membresia.data.id,
        fecha_hora_entrada=entrada or hora_local(),
        fecha_hora_salida=getattr(getattr(form, "fecha_hora_salida", None), "data", None),
    )
    try:
        excluir = (request.view_args or {}).get("pk") if has_request_context() else None
        validar_asistencia(candidato, excluir_id=int(excluir) if excluir else None)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


class AsistenciaModelView(ModelView):
    datamodel = SQLAInterface(Asistencia, db.session)
    route_base = "/asistencias"
    can_delete = False
    exclude_route_methods = {"delete"}
    list_title = "Asistencias"
    add_title = "Registrar entrada"
    edit_title = "Corregir asistencia"
    show_title = "Información de asistencia"
    list_columns = ["socio", "membresia", "fecha_hora_entrada", "fecha_hora_salida", "estado"]
    show_columns = list_columns + ["observaciones", "anulada"]
    add_columns = ["socio", "membresia", "observaciones"]
    edit_columns = ["socio", "membresia", "fecha_hora_entrada", "fecha_hora_salida", "observaciones"]
    # ``estado`` is a hybrid property; FAB's search form only accepts mapped fields.
    search_columns = ["socio", "fecha_hora_entrada", "membresia"]
    label_columns = {"socio": "Socio", "membresia": "Membresía", "fecha_hora_entrada": "Entrada", "fecha_hora_salida": "Salida", "estado": "Estado", "observaciones": "Observaciones", "anulada": "Anulada"}
    edit_form_extra_fields = {
        "fecha_hora_entrada": DateTimeField("Fecha y hora de entrada", validators=[validar_reglas_asistencia]),
        "fecha_hora_salida": DateTimeField("Fecha y hora de salida", validators=[Optional(), validar_reglas_asistencia]),
    }
    base_order = ("fecha_hora_entrada", "desc")
    validators_columns = {"fecha_hora_entrada": [validar_reglas_asistencia]}

    def pre_add(self, item):
        item.fecha_hora_entrada = item.fecha_hora_entrada or hora_local()
        validar_asistencia(item)

    def pre_update(self, item):
        validar_asistencia(item, excluir_id=item.id)

    @action("registrar_salida", "Registrar salida", "¿Registrar la salida ahora?", "fa-sign-out")
    def registrar_salida_seleccionada(self, items):
        try:
            for asistencia in (items if isinstance(items, list) else [items]):
                registrar_salida(asistencia)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "warning")
            return redirect(self.get_redirect())
        flash("Salida registrada.", "success")
        return redirect(self.get_redirect())

    @action("anular", "Anular", "¿Anular las asistencias seleccionadas?", "fa-ban")
    def anular(self, items):
        seleccionadas = items if isinstance(items, list) else [items]
        for asistencia in seleccionadas:
            asistencia.anulada = True
            asistencia.fecha_anulacion = hora_local()
            asistencia.motivo_anulacion = "Anulada por usuario administrador"
        db.session.commit()
        flash("Asistencias anuladas; el historial se conservó.", "success")
        return redirect(self.get_redirect())
