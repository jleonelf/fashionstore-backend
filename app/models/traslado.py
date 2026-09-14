"""Modelos Ciclo 2 — Traslados entre sucursales (CU09).

Alineados con docu_general/fashionstore-base-datos-final.sql (banner CICLO 2).
Agregado Entrega 1: clave_idempotencia / hash_solicitud y enlace opcional
detalle_traslado -> detalle_reserva (trazabilidad por linea, decision RN-02).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, ForeignKey, DateTime,
    UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def _ahora_utc():
    return datetime.now(timezone.utc)


EstadoTraslado = ENUM(
    "SOLICITADO", "APROBADO", "RECHAZADO", "DESPACHADO", "RECIBIDO", "CANCELADO",
    name="estado_traslado", schema="inventario", create_type=False,
)


class Traslado(Base):
    __tablename__ = "traslados"
    __table_args__ = (
        CheckConstraint(
            "sucursal_origen_id <> sucursal_destino_id",
            name="ck_traslados_origen_destino_distintos",
        ),
        {"schema": "inventario"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reserva_id = Column(UUID(as_uuid=True), ForeignKey("comercial.reservas.id"), nullable=True)
    sucursal_origen_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=False)
    sucursal_destino_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=False)
    estado = Column(EstadoTraslado, nullable=False, default="SOLICITADO")
    solicitado_por_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=False)
    aprobado_por_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=True)
    fecha_solicitud = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)
    fecha_aprobacion = Column(DateTime(timezone=True), nullable=True)
    fecha_despacho = Column(DateTime(timezone=True), nullable=True)
    fecha_recepcion = Column(DateTime(timezone=True), nullable=True)
    motivo_rechazo = Column(Text, nullable=True)
    # Idempotencia (plan Ciclo 2)
    clave_idempotencia = Column(UUID(as_uuid=True), nullable=True, unique=True)
    hash_solicitud = Column(Text, nullable=True)

    detalles = relationship("DetalleTraslado", back_populates="traslado", cascade="all, delete-orphan")


class DetalleTraslado(Base):
    __tablename__ = "detalles_traslado"
    __table_args__ = (
        UniqueConstraint("traslado_id", "variante_id", name="uq_detalles_traslado_traslado_variante"),
        CheckConstraint("cantidad > 0", name="ck_detalle_traslado_cantidad_pos"),
        {"schema": "inventario"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    traslado_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventario.traslados.id", ondelete="CASCADE"),
        nullable=False,
    )
    detalle_reserva_id = Column(
        UUID(as_uuid=True),
        ForeignKey("comercial.detalles_reserva.id"),
        nullable=True,
    )
    variante_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.variantes_producto.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)

    traslado = relationship("Traslado", back_populates="detalles")
