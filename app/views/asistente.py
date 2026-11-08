"""Pantalla para preguntar sobre indicadores agregados autorizados."""

from flask import current_app, make_response
from flask_appbuilder import BaseView, expose, has_access
from flask_appbuilder.security.decorators import permission_name
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import TextAreaField
from wtforms.validators import Length

from app.services_asistente import (
    AsistenteNoConfigurado,
    construir_contexto,
    responder_pregunta,
)


class PreguntaForm(FlaskForm):
    pregunta = TextAreaField("Pregunta", validators=[Length(min=3, max=500)])


class AsistenteView(BaseView):
    route_base = "/asistente"
    default_view = "index"

    @expose("/", methods=["GET", "POST"])
    @has_access
    @permission_name("consultar")
    @login_required
    def index(self):
        form = PreguntaForm()
        pregunta = ""
        respuesta = None
        error = None
        if form.validate_on_submit():
            pregunta = (form.pregunta.data or "").strip()
            if len(pregunta) < 3:
                error = "Escribe una pregunta de entre 3 y 500 caracteres."
            else:
                administrador = any(rol.name == "Admin" for rol in current_user.roles)
                try:
                    contexto = construir_contexto(administrador=administrador)
                    respuesta = responder_pregunta(pregunta, contexto)
                except AsistenteNoConfigurado:
                    error = "El asistente todavía no está configurado. Configura OPENAI_API_KEY en el entorno del servidor."
                except Exception as exc:
                    current_app.logger.error(
                        "Falló la consulta al asistente IA (%s).", type(exc).__name__,
                    )
                    error = "No se pudo obtener una respuesta ahora. Inténtalo nuevamente más tarde."
        elif form.is_submitted():
            error = "Escribe una pregunta de entre 3 y 500 caracteres."

        resultado = self.render_template(
            "asistente/index.html",
            form=form,
            pregunta=pregunta,
            respuesta=respuesta,
            error=error,
            solo_membresias_y_asistencias=not any(
                rol.name == "Admin" for rol in current_user.roles
            ),
        )
        response = make_response(resultado)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
