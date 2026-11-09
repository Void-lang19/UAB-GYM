"""Reglas de negocio transaccionales para membresías, pagos y asistencias."""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, inspect
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Asistencia, Membresia, Pago, Plan, Socio
from app.timeutils import ZONA_LA_PAZ

METODOS_PAGO = ("Efectivo", "Transferencia bancaria", "QR", "Otro")


def hora_local() -> datetime:
    """Devuelve hora local de La Paz sin tzinfo, para columnas DateTime existentes."""
    return datetime.now(ZONA_LA_PAZ).replace(tzinfo=None)


def preparar_membresia(membresia: Membresia, *, excluir_id: int | None = None) -> None:
    existente = db.session.get(Membresia, excluir_id) if excluir_id is not None else None
    # En formularios de Flask-AppBuilder se puede asignar primero la relación
    # (membresia.socio / membresia.plan); SQLAlchemy sincroniza las FK al hacer
    # flush, por lo que socio_id y plan_id todavía pueden ser None aquí.
    socio_id = membresia.socio_id or getattr(membresia.socio, "id", None)
    socio = None
    if socio_id is not None:
        socio = db.session.execute(
            db.select(Socio).where(Socio.id == socio_id).with_for_update()
        ).scalar_one_or_none()
    plan_id = membresia.plan_id or getattr(membresia.plan, "id", None)
    plan = db.session.get(Plan, plan_id) if plan_id is not None else None
    if socio is None:
        raise ValueError("El socio seleccionado no existe.")
    if socio.estado != "activo":
        raise ValueError("No se pueden crear membresías para socios inactivos.")
    if plan is None:
        raise ValueError("El plan seleccionado no existe.")
    if plan.estado != "activo":
        raise ValueError("No se pueden contratar planes inactivos.")
    if not membresia.fecha_inicio:
        raise ValueError("La fecha de inicio es obligatoria.")

    # Deja las claves explícitas para que las validaciones y consultas siguientes
    # funcionen antes del flush del formulario.
    membresia.socio_id = socio.id
    membresia.plan_id = plan.id
    membresia.fecha_fin = membresia.fecha_inicio + timedelta(days=plan.duracion_dias - 1)
    historial_plan = inspect(membresia).attrs.plan_id.history.deleted
    plan_modificado = bool(historial_plan and historial_plan[0] != plan.id)
    if existente is None or plan_modificado:
        membresia.precio_pactado = Decimal(plan.precio)
    membresia.estado = membresia.estado or "activa"
    consulta = db.select(Membresia.id).where(
        Membresia.socio_id == socio.id,
        Membresia.estado == "activa",
        Membresia.fecha_inicio <= membresia.fecha_fin,
        Membresia.fecha_fin >= membresia.fecha_inicio,
    )
    if excluir_id is not None:
        consulta = consulta.where(Membresia.id != excluir_id)
    if db.session.execute(consulta.limit(1)).first():
        raise ValueError("El socio ya tiene una membresía activa en ese período.")


def cancelar_membresia(membresia: Membresia, motivo: str = "Cancelada por usuario autorizado") -> None:
    if membresia.estado == "cancelada":
        raise ValueError("La membresía ya está cancelada.")
    membresia.estado = "cancelada"
    membresia.fecha_cancelacion = hora_local()
    membresia.motivo_cancelacion = motivo.strip()
    db.session.commit()


def renovar_membresia(membresia: Membresia, fecha_inicio: date | None = None) -> Membresia:
    inicio = fecha_inicio or max(date.today(), membresia.fecha_fin + timedelta(days=1))
    nueva = Membresia(
        socio_id=membresia.socio_id,
        plan_id=membresia.plan_id,
        fecha_inicio=inicio,
        observaciones=f"Renovación de membresía #{membresia.id}",
    )
    preparar_membresia(nueva)
    db.session.add(nueva)
    db.session.commit()
    return nueva


def total_pagado(membresia_id: int, *, excluir_pago_id: int | None = None) -> Decimal:
    consulta = db.select(func.coalesce(func.sum(Pago.monto), 0)).where(
        Pago.membresia_id == membresia_id, Pago.estado == "valido"
    )
    if excluir_pago_id is not None:
        consulta = consulta.where(Pago.id != excluir_pago_id)
    return Decimal(db.session.execute(consulta).scalar_one())


def validar_pago(pago: Pago, *, excluir_pago_id: int | None = None) -> None:
    membresia_id = pago.membresia_id or getattr(pago.membresia, "id", None)
    membresia = None
    if membresia_id is not None:
        membresia = db.session.execute(
            db.select(Membresia).where(Membresia.id == membresia_id).with_for_update()
        ).scalar_one_or_none()
    if membresia is None:
        raise ValueError("La membresía seleccionada no existe.")
    pago.membresia_id = membresia.id
    try:
        monto = Decimal(str(pago.monto))
    except (InvalidOperation, TypeError):
        raise ValueError("El monto debe ser un importe decimal válido.") from None
    if not monto.is_finite() or monto <= 0:
        raise ValueError("El monto del pago debe ser mayor que cero.")
    if pago.metodo_pago not in METODOS_PAGO:
        raise ValueError("Selecciona un método de pago válido.")
    if (pago.estado or "valido") == "valido" and total_pagado(membresia.id, excluir_pago_id=excluir_pago_id) + monto > Decimal(membresia.precio_pactado):
        raise ValueError("El pago supera el saldo pendiente de la membresía.")
    pago.monto = monto


def anular_pago(pago: Pago, motivo: str) -> None:
    if pago.estado == "anulado":
        raise ValueError("El pago ya está anulado.")
    if not motivo.strip():
        raise ValueError("Indica el motivo de anulación.")
    db.session.execute(
        db.select(Membresia.id).where(Membresia.id == pago.membresia_id).with_for_update()
    ).scalar_one()
    pago.estado = "anulado"
    pago.fecha_anulacion = hora_local()
    pago.motivo_anulacion = motivo.strip()
    db.session.commit()


def registrar_entrada(socio_id: int, *, cuando: datetime | None = None) -> Asistencia:
    socio = db.session.execute(
        db.select(Socio).where(Socio.id == socio_id).with_for_update()
    ).scalar_one_or_none()
    if socio is None:
        raise ValueError("El socio no existe.")
    if socio.estado != "activo":
        raise ValueError("No se puede registrar el ingreso de un socio inactivo.")
    abierto = db.session.execute(db.select(Asistencia.id).where(
        Asistencia.socio_id == socio_id,
        Asistencia.fecha_hora_salida.is_(None),
        Asistencia.anulada.is_(False),
    ).limit(1)).first()
    if abierto:
        raise ValueError("El socio ya tiene una asistencia abierta.")
    hora = cuando or hora_local()
    membresias = db.session.execute(db.select(Membresia).where(
        Membresia.socio_id == socio_id,
        Membresia.estado == "activa",
        Membresia.fecha_inicio <= hora.date(),
        Membresia.fecha_fin >= hora.date(),
    ).with_for_update()).scalars().all()
    if not membresias:
        raise ValueError("No se puede registrar el ingreso: el socio no tiene una membresía vigente.")
    asistencia = Asistencia(socio_id=socio_id, membresia_id=membresias[0].id, fecha_hora_entrada=hora)
    db.session.add(asistencia)
    db.session.commit()
    return asistencia


def registrar_salida(asistencia: Asistencia, *, cuando: datetime | None = None) -> None:
    if asistencia.anulada:
        raise ValueError("No se puede cerrar una asistencia anulada.")
    if asistencia.fecha_hora_salida is not None:
        raise ValueError("La asistencia ya tiene una salida registrada.")
    hora = cuando or hora_local()
    if hora < asistencia.fecha_hora_entrada:
        raise ValueError("La salida no puede ser anterior a la entrada.")
    asistencia.fecha_hora_salida = hora
    db.session.commit()


def validar_asistencia(asistencia: Asistencia, *, excluir_id: int | None = None) -> None:
    socio_id = asistencia.socio_id or getattr(asistencia.socio, "id", None)
    membresia_id = asistencia.membresia_id or getattr(asistencia.membresia, "id", None)
    socio = None
    if socio_id is not None:
        socio = db.session.execute(
            db.select(Socio).where(Socio.id == socio_id).with_for_update()
        ).scalar_one_or_none()
    membresia = None
    if membresia_id is not None:
        membresia = db.session.execute(
            db.select(Membresia).where(Membresia.id == membresia_id).with_for_update()
        ).scalar_one_or_none()
    if socio is None or membresia is None:
        raise ValueError("Selecciona un socio y una membresía existentes.")
    asistencia.socio_id = socio.id
    asistencia.membresia_id = membresia.id
    if membresia.socio_id != socio.id:
        raise ValueError("La membresía seleccionada no pertenece al socio.")
    instante = asistencia.fecha_hora_entrada or hora_local()
    if socio.estado != "activo" or membresia.estado != "activa" or not (membresia.fecha_inicio <= instante.date() <= membresia.fecha_fin):
        raise ValueError("El socio no tiene una membresía vigente en la fecha de ingreso.")
    if asistencia.fecha_hora_salida and asistencia.fecha_hora_salida < instante:
        raise ValueError("La salida no puede ser anterior a la entrada.")
    consulta = db.select(Asistencia.id).where(
        Asistencia.socio_id == socio.id,
        Asistencia.fecha_hora_salida.is_(None),
        Asistencia.anulada.is_(False),
    )
    if excluir_id is not None:
        consulta = consulta.where(Asistencia.id != excluir_id)
    if asistencia.fecha_hora_salida is None and db.session.execute(consulta.limit(1)).first():
        raise ValueError("El socio ya tiene una asistencia abierta.")
