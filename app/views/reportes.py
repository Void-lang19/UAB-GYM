"""Tres pantallas de consulta protegidas por permisos de Flask-AppBuilder."""

from dataclasses import asdict

from flask import current_app, make_response, request, send_file, url_for
from flask_appbuilder import BaseView, expose, has_access
from flask_appbuilder.security.decorators import permission_name
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Plan
from app.reportes_csv import crear_archivo_csv, formatear_valor
from app.reportes_filtros import (
    ESTADOS_ASISTENCIA, ESTADOS_MEMBRESIA, ESTADOS_PAGO,
    FiltroInvalido, PARAMETROS, validar_filtros,
)
from app.services import METODOS_PAGO
from app.services_reportes import COLUMNAS, filas_exportacion, obtener_reporte

TITULOS = {
    "membresias": "Reporte de membresías",
    "pagos": "Reporte de ingresos y pagos",
    "asistencias": "Reporte de asistencias",
}
NOMBRES_CSV = {
    "membresias": "reporte_membresias.csv",
    "pagos": "reporte_ingresos_pagos.csv",
    "asistencias": "reporte_asistencias.csv",
}
INDICADORES = {
    "membresias": (("total", "Total de membresías"), ("vigentes", "Vigentes"),
                   ("vencidas", "Vencidas"), ("proximas", "Próximas a vencer"),
                   ("canceladas", "Canceladas"), ("programadas", "Programadas")),
    "pagos": (("ingresos", "Ingresos recibidos"), ("cantidad_pagos", "Pagos válidos"),
              ("anulados", "Pagos anulados"), ("saldo", "Saldo pendiente actual")),
    "asistencias": (("total", "Asistencias válidas"), ("socios_unicos", "Socios diferentes"),
                    ("abiertas", "Abiertas"), ("cerradas", "Cerradas")),
}


def _campos(tipo, planes):
    campos = [("socio", "Buscar socio por nombre", "text", ()),
              ("socio_id", "ID de socio (opcional)", "number", ())]
    if tipo in ("membresias", "pagos"):
        campos.append(("plan_id", "Plan", "select", [(str(p.id), p.nombre) for p in planes]))
    if tipo == "asistencias":
        campos.append(("membresia_id", "ID de membresía (opcional)", "number", ()))
    estados = {"membresias": ESTADOS_MEMBRESIA, "pagos": ESTADOS_PAGO, "asistencias": ESTADOS_ASISTENCIA}
    campos.append(("estado", "Estado", "select", [(x, x.capitalize()) for x in estados[tipo]]))
    if tipo == "membresias":
        campos.extend((clave, titulo, "date", ()) for clave, titulo in (
            ("fecha_referencia", "Vigencia a la fecha"),
            ("inicio_desde", "Inicio del contrato: desde"), ("inicio_hasta", "Inicio del contrato: hasta"),
            ("vencimiento_desde", "Vencimiento: desde"), ("vencimiento_hasta", "Vencimiento: hasta"),
        ))
        campos.append(("dias_por_vencer", "Próximos a vencer: días (0–365)", "number", ()))
    else:
        campos.extend((clave, titulo, "date", ()) for clave, titulo in (
            ("fecha_desde", "Fecha inicial (La Paz)"), ("fecha_hasta", "Fecha final (La Paz)"),
        ))
    if tipo == "pagos":
        campos.append(("metodo_pago", "Método de pago", "select", [(x, x) for x in METODOS_PAGO]))
    campos.append(("por_pagina", "Filas por página", "select", [(str(n), str(n)) for n in (10, 25, 50, 100)]))
    return campos


class ReporteBaseView(BaseView):
    default_view = "index"
    tipo = None

    def _filtros(self):
        return validar_filtros(
            self.tipo, request.args,
            dias_predeterminados=current_app.config.get("REPORTES_DIAS_POR_VENCER", 7),
        )

    def _respuesta(self, contenido, estado=200):
        respuesta = make_response(contenido, estado)
        respuesta.headers["Cache-Control"] = "private, no-store"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        return respuesta

    def _error(self, mensaje, estado):
        return self._respuesta(self.render_template(
            "reportes/error.html", titulo=TITULOS[self.tipo], mensaje=mensaje,
            volver=url_for(f"{self.endpoint}.index"),
        ), estado)

    @expose("/", methods=["GET"])
    @has_access
    @permission_name("consultar")
    @login_required
    def index(self):
        try:
            filtros = self._filtros()
            resultado = obtener_reporte(filtros)
            with db.session.no_autoflush:
                planes = []
                if self.tipo != "asistencias":
                    planes = db.session.execute(
                        db.select(Plan.id, Plan.nombre).order_by(Plan.nombre)
                    ).all()
        except FiltroInvalido as exc:
            return self._error(str(exc), 400)
        except SQLAlchemyError:
            current_app.logger.exception("No se pudo consultar el reporte %s.", self.tipo)
            return self._error("No se pudo consultar el reporte. Inténtalo nuevamente más tarde.", 500)

        valores = {
            k: formatear_valor(v) for k, v in asdict(filtros).items()
            if k in PARAMETROS[self.tipo] and v is not None
        }

        def enlace_pagina(clave, numero):
            return url_for(f"{self.endpoint}.index", **{**valores, clave: numero})

        parametros_csv = {k: v for k, v in valores.items() if not k.startswith("pagina") and k != "por_pagina"}
        return self._respuesta(self.render_template(
            f"reportes/{self.tipo}.html", titulo=TITULOS[self.tipo],
            filtros=filtros, valores=valores, campos=_campos(self.tipo, planes),
            columnas=COLUMNAS[self.tipo], etiquetas=INDICADORES[self.tipo],
            formatear=formatear_valor, enlace_pagina=enlace_pagina,
            url_limpiar=url_for(f"{self.endpoint}.index"),
            url_csv=url_for(f"{self.endpoint}.exportar", **parametros_csv),
            **resultado,
        ))

    @expose("/exportar.csv", methods=["GET"])
    @has_access
    @permission_name("consultar")
    @login_required
    def exportar(self):
        try:
            filtros = self._filtros()
            archivo = crear_archivo_csv(COLUMNAS[self.tipo], filas_exportacion(filtros))
        except FiltroInvalido as exc:
            return self._error(str(exc), 400)
        except (SQLAlchemyError, OSError):
            current_app.logger.exception("No se pudo exportar el reporte %s.", self.tipo)
            return self._error("No se pudo generar el archivo. Inténtalo nuevamente más tarde.", 500)
        try:
            respuesta = send_file(
                archivo, mimetype="text/csv", as_attachment=True,
                download_name=NOMBRES_CSV[self.tipo], conditional=False, etag=False,
            )
        except BaseException:
            archivo.close()
            raise
        respuesta.call_on_close(archivo.close)
        respuesta.headers["Cache-Control"] = "private, no-store"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        return respuesta


class ReporteMembresiasView(ReporteBaseView):
    route_base = "/reportes/membresias"
    tipo = "membresias"


class ReportePagosView(ReporteBaseView):
    route_base = "/reportes/pagos"
    tipo = "pagos"


class ReporteAsistenciasView(ReporteBaseView):
    route_base = "/reportes/asistencias"
    tipo = "asistencias"
