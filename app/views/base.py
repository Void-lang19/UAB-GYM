import logging
from typing import Protocol

from flask import Response, flash, redirect
from flask_appbuilder import ModelView, action
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

ESTADO_CHOICES = (("activo", "Activo"), ("inactivo", "Inactivo"))


class Desactivable(Protocol):
    estado: str


class SoftDeactivateModelView(ModelView):
    entity_plural = "registros"
    estado_inactivo = "inactivo"
    can_delete = False
    exclude_route_methods = {"delete"}

    @action(
        "desactivar",
        "Desactivar",
        "¿Desactivar los registros seleccionados? Sus datos se conservarán.",
        "fa-user-slash",
    )
    def desactivar(self, items: Desactivable | list[Desactivable]) -> Response:
        registros = items if isinstance(items, list) else [items]
        activos = [registro for registro in registros if registro.estado != self.estado_inactivo]
        if not activos:
            flash(
                f"Los {self.entity_plural} seleccionados ya están inactivos.",
                "info",
            )
            return redirect(self.get_redirect())

        try:
            for registro in activos:
                registro.estado = self.estado_inactivo
                self.datamodel.edit(registro, commit=False)
            self.datamodel.session.commit()
        except SQLAlchemyError:
            self.datamodel.session.rollback()
            logger.exception(
                "No se pudieron desactivar los %s seleccionados.",
                self.entity_plural,
            )
            flash(
                f"No se pudieron desactivar los {self.entity_plural}. "
                "Inténtalo nuevamente.",
                "danger",
            )
            return redirect(self.get_redirect())

        flash(
            f"Se desactivaron {len(activos)} {self.entity_plural}.",
            "success",
        )
        return redirect(self.get_redirect())
