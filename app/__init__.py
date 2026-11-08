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

    @app.cli.command("check-db")
    def check_db() -> None:
        with db.engine.connect() as connection:
            version, database = connection.execute(
                text("SELECT VERSION(), DATABASE()")
            ).one()
        click.echo(f"Conexión correcta: {database} (servidor {version}).")

    return app
