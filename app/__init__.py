import click
from flask import Flask
from flask_appbuilder import AppBuilder
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from config import load_config

db = SQLAlchemy()
appbuilder = AppBuilder()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config())

    db.init_app(app)
    with app.app_context():
        appbuilder.init_app(app, db.session)
        from app.views import EntrenadorModelView, SocioModelView

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
        click.echo(
            "Tablas creadas o ya existentes: socios, entrenadores y planes."
        )

    return app
