from datetime import date

from sqlalchemy import CheckConstraint, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.sql import func, text

from app import db


class Socio(db.Model):
    __tablename__ = "socios"
    __table_args__ = (
        UniqueConstraint("documento_identidad", name="uq_socios_documento"),
        UniqueConstraint("correo_electronico", name="uq_socios_correo"),
        CheckConstraint(
            "estado IN ('activo', 'inactivo')",
            name="ck_socios_estado",
        ),
        Index("ix_socios_apellidos_nombres", "apellidos", "nombres"),
        Index("ix_socios_estado", "estado"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(String(100), nullable=False)
    apellidos = db.Column(String(100), nullable=False)
    documento_identidad = db.Column(String(30), nullable=False)
    telefono = db.Column(String(25))
    correo_electronico = db.Column(String(254))
    fecha_nacimiento = db.Column(db.Date)
    direccion = db.Column(String(255))
    fecha_registro = db.Column(
        db.Date,
        nullable=False,
        default=date.today,
        server_default=func.current_date(),
    )
    estado = db.Column(
        String(10),
        nullable=False,
        default="activo",
        server_default=text("'activo'"),
    )

    def __repr__(self) -> str:
        return f"{self.nombres} {self.apellidos}"


class Entrenador(db.Model):
    __tablename__ = "entrenadores"
    __table_args__ = (
        UniqueConstraint("documento_identidad", name="uq_entrenadores_documento"),
        UniqueConstraint("correo_electronico", name="uq_entrenadores_correo"),
        CheckConstraint(
            "estado IN ('activo', 'inactivo')",
            name="ck_entrenadores_estado",
        ),
        Index("ix_entrenadores_apellidos_nombres", "apellidos", "nombres"),
        Index("ix_entrenadores_estado", "estado"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(String(100), nullable=False)
    apellidos = db.Column(String(100), nullable=False)
    documento_identidad = db.Column(String(30), nullable=False)
    telefono = db.Column(String(25))
    correo_electronico = db.Column(String(254))
    especialidad = db.Column(String(120), nullable=False)
    fecha_contratacion = db.Column(db.Date, nullable=False)
    estado = db.Column(
        String(10),
        nullable=False,
        default="activo",
        server_default=text("'activo'"),
    )

    def __repr__(self) -> str:
        return f"{self.nombres} {self.apellidos}"


class Plan(db.Model):
    __tablename__ = "planes"
    __table_args__ = (
        CheckConstraint("duracion_dias > 0", name="ck_planes_duracion_positiva"),
        CheckConstraint("precio >= 0", name="ck_planes_precio_no_negativo"),
        CheckConstraint(
            "estado IN ('activo', 'inactivo')",
            name="ck_planes_estado",
        ),
        Index("ix_planes_estado", "estado"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(String(100), nullable=False, unique=True)
    descripcion = db.Column(Text)
    duracion_dias = db.Column(db.Integer, nullable=False)
    precio = db.Column(Numeric(10, 2), nullable=False)
    beneficios = db.Column(Text)
    estado = db.Column(
        String(10),
        nullable=False,
        default="activo",
        server_default=text("'activo'"),
    )

    def __repr__(self) -> str:
        return self.nombre
