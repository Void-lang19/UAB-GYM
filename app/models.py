from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, case
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func, text

from app import db
from app.timeutils import ZONA_LA_PAZ


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
    membresias = db.relationship("Membresia", back_populates="socio")
    asistencias = db.relationship("Asistencia", back_populates="socio")

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
    membresias = db.relationship("Membresia", back_populates="plan")

    def __repr__(self) -> str:
        return self.nombre


class Membresia(db.Model):
    __tablename__ = "membresias"
    __table_args__ = (
        CheckConstraint("fecha_fin >= fecha_inicio", name="ck_membresias_fechas"),
        CheckConstraint("precio_pactado >= 0", name="ck_membresias_precio_no_negativo"),
        CheckConstraint("estado IN ('activa', 'cancelada')", name="ck_membresias_estado"),
        Index("ix_membresias_socio_periodo", "socio_id", "fecha_inicio", "fecha_fin"),
        Index("ix_membresias_plan", "plan_id"),
        Index("ix_membresias_estado", "estado"),
    )

    id = db.Column(db.Integer, primary_key=True)
    socio_id = db.Column(db.Integer, ForeignKey("socios.id", ondelete="RESTRICT"), nullable=False)
    plan_id = db.Column(db.Integer, ForeignKey("planes.id", ondelete="RESTRICT"), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    precio_pactado = db.Column(Numeric(10, 2), nullable=False)
    estado = db.Column(String(12), nullable=False, default="activa", server_default=text("'activa'"))
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=func.current_timestamp())
    observaciones = db.Column(Text)
    fecha_cancelacion = db.Column(db.DateTime)
    motivo_cancelacion = db.Column(String(255))

    socio = db.relationship("Socio", back_populates="membresias")
    plan = db.relationship("Plan", back_populates="membresias")
    pagos = db.relationship("Pago", back_populates="membresia")
    asistencias = db.relationship("Asistencia", back_populates="membresia")

    @hybrid_property
    def vigencia(self) -> str:
        if self.estado == "cancelada":
            return "cancelada"
        hoy = datetime.now(ZONA_LA_PAZ).date()
        if self.fecha_inicio > hoy:
            return "programada"
        if self.fecha_fin < hoy:
            return "vencida"
        return "vigente"

    @vigencia.expression
    def vigencia(cls):
        hoy = datetime.now(ZONA_LA_PAZ).date()
        return case(
            (cls.estado == "cancelada", "cancelada"),
            (cls.fecha_inicio > hoy, "programada"),
            (cls.fecha_fin < hoy, "vencida"),
            else_="vigente",
        )

    @property
    def total_pagado(self):
        from sqlalchemy import func as sql_func
        total = db.session.query(sql_func.coalesce(sql_func.sum(Pago.monto), 0)).filter(
            Pago.membresia_id == self.id, Pago.estado == "valido"
        ).scalar()
        return total

    @property
    def saldo_pendiente(self):
        return self.precio_pactado - self.total_pagado

    def __repr__(self) -> str:
        return f"Membresía #{self.id} - {self.socio}"


class Pago(db.Model):
    __tablename__ = "pagos"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_pagos_monto_positivo"),
        CheckConstraint("estado IN ('valido', 'anulado')", name="ck_pagos_estado"),
        CheckConstraint("metodo_pago IN ('Efectivo', 'Transferencia bancaria', 'QR', 'Otro')", name="ck_pagos_metodo"),
        Index("ix_pagos_membresia_estado", "membresia_id", "estado"),
        Index("ix_pagos_fecha", "fecha_pago"),
    )

    id = db.Column(db.Integer, primary_key=True)
    membresia_id = db.Column(db.Integer, ForeignKey("membresias.id", ondelete="RESTRICT"), nullable=False)
    fecha_pago = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=func.current_timestamp())
    monto = db.Column(Numeric(10, 2), nullable=False)
    metodo_pago = db.Column(String(30), nullable=False)
    referencia = db.Column(String(120))
    estado = db.Column(String(10), nullable=False, default="valido", server_default=text("'valido'"))
    observaciones = db.Column(Text)
    fecha_anulacion = db.Column(db.DateTime)
    motivo_anulacion = db.Column(String(255))

    membresia = db.relationship("Membresia", back_populates="pagos")

    def __repr__(self) -> str:
        return f"Pago #{self.id} - {self.monto}"


class Asistencia(db.Model):
    __tablename__ = "asistencias"
    __table_args__ = (
        CheckConstraint("fecha_hora_salida IS NULL OR fecha_hora_salida >= fecha_hora_entrada", name="ck_asistencias_horas"),
        Index("ix_asistencias_socio_entrada", "socio_id", "fecha_hora_entrada"),
        Index("ix_asistencias_membresia", "membresia_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    socio_id = db.Column(db.Integer, ForeignKey("socios.id", ondelete="RESTRICT"), nullable=False)
    membresia_id = db.Column(db.Integer, ForeignKey("membresias.id", ondelete="RESTRICT"), nullable=False)
    fecha_hora_entrada = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_hora_salida = db.Column(db.DateTime)
    observaciones = db.Column(Text)
    anulada = db.Column(db.Boolean, nullable=False, default=False, server_default=text("0"))
    fecha_anulacion = db.Column(db.DateTime)
    motivo_anulacion = db.Column(String(255))

    socio = db.relationship("Socio", back_populates="asistencias")
    membresia = db.relationship("Membresia", back_populates="asistencias")

    @hybrid_property
    def estado(self) -> str:
        return "anulada" if self.anulada else ("abierta" if self.fecha_hora_salida is None else "cerrada")

    @estado.expression
    def estado(cls):
        return case(
            (cls.anulada.is_(True), "anulada"),
            (cls.fecha_hora_salida.is_(None), "abierta"),
            else_="cerrada",
        )

    def __repr__(self) -> str:
        return f"Asistencia #{self.id} - {self.socio}"
