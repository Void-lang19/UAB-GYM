from flask import Flask

from app import db
from app import models  # noqa: F401

app = Flask("uab_gym_modulos_tests")
app.config.update(
    SECRET_KEY="testing-secret-key-that-is-long-enough-for-flask",
    SQLALCHEMY_DATABASE_URI="sqlite://",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    WTF_CSRF_ENABLED=False,
)
db.init_app(app)


def limpiar_base() -> None:
    db.drop_all()
    db.create_all()


def crear_datos_basicos():
    from decimal import Decimal
    from app.models import Plan, Socio

    socio = Socio(nombres="Ana", apellidos="Prueba", documento_identidad="TEST-1")
    plan = Plan(nombre="Mensual", duracion_dias=30, precio=Decimal("200.00"), estado="activo")
    db.session.add_all([socio, plan])
    db.session.commit()
    return socio, plan
