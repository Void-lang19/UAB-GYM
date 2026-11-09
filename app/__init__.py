import click
from flask import Flask, session
from flask_appbuilder import AppBuilder
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from config import load_config

db = SQLAlchemy()
appbuilder = AppBuilder()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config())

    @app.before_request
    def use_supported_locale() -> None:
        idiomas = app.config["LANGUAGES"]
        idioma_predeterminado = app.config["BABEL_DEFAULT_LOCALE"]
        if session.get("locale") not in idiomas:
            session["locale"] = idioma_predeterminado

    db.init_app(app)
    with app.app_context():
        appbuilder.init_app(app, db.session)
        from app.views import (
            AsistenciaModelView, EntrenadorModelView, MembresiaModelView,
            PagoModelView, PlanModelView, SocioModelView,
            ReporteAsistenciasView, ReporteMembresiasView, ReportePagosView,
        )

        appbuilder.add_view(
            SocioModelView,
            "Socios",
            icon="fa-users",
            category="Gimnasio",
            category_icon="fa-dumbbell",
        )
        appbuilder.add_view(
            EntrenadorModelView,
            "Entrenadores",
            icon="fa-user-tie",
            category="Gimnasio",
        )
        appbuilder.add_view(
            PlanModelView,
            "Planes",
            icon="fa-list-alt",
            category="Gimnasio",
        )
        appbuilder.add_view(MembresiaModelView, "Membresías", icon="fa-id-card", category="Gimnasio")
        appbuilder.add_view(PagoModelView, "Pagos", icon="fa-money", category="Gimnasio")
        appbuilder.add_view(AsistenciaModelView, "Asistencias", icon="fa-calendar-check-o", category="Gimnasio")
        appbuilder.add_view(
            ReporteMembresiasView, "Reporte de membresías",
            icon="fa-id-card", category="Reportes", category_icon="fa-bar-chart",
        )
        appbuilder.add_view(
            ReportePagosView, "Reporte de ingresos y pagos",
            icon="fa-money", category="Reportes",
        )
        appbuilder.add_view(
            ReporteAsistenciasView, "Reporte de asistencias",
            icon="fa-calendar-check-o", category="Reportes",
        )

    @app.cli.command("check-db")
    def check_db() -> None:
        with db.engine.connect() as connection:
            version, database = connection.execute(
                text("SELECT VERSION(), DATABASE()")
            ).one()
        click.echo(f"Conexión correcta: {database} (servidor {version}).")

    @app.cli.command("init-db")
    def init_db() -> None:
        from app import models

        db.create_all()
        click.echo("Tablas creadas o ya existentes: socios, entrenadores, planes, membresias, pagos y asistencias.")

    @app.cli.command("configure-roles")
    def configure_roles() -> None:
        from app.security import configure_application_roles

        configure_application_roles(appbuilder.sm)
        click.echo(
            "Roles Recepcionista y Entrenador configurados. "
            "Admin y Public permanecen sin cambios."
        )

    @app.cli.command("seed-demo")
    def seed_demo() -> None:
        """Carga datos de ejemplo del prototipo sin duplicarlos."""
        from app.seed_demo import cargar_datos_demo

        creados = cargar_datos_demo()
        click.echo("Datos de ejemplo agregados (solo se muestran cantidades):")
        for entidad, cantidad in creados.items():
            click.echo(f"  {entidad}: {cantidad}")
        click.echo("La carga es repetible y no reemplaza registros existentes.")

    return app
