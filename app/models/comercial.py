"""Modelos Ciclo 2 — Comercial: reservas, ventas y pagos (CU08, CU11-CU13, CU23-CU24).

Alineados con docu_general/fashionstore-base-datos-final.sql (banner CICLO 2)
mas los agregados de Entrega 1 del plan:
  - clave_idempotencia / hash_solicitud (Idempotency-Key obligatorio)
  - snapshot de politica de adelanto en reserva
  - cantidades y estado por linea en detalles_reserva
  - enlace detalle_venta -> detalle_reserva (venta parcial / devolucion)
No crear tablas de Ciclo 3 (carritos, pedidos_entrega, promociones, IA).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, Numeric, ForeignKey, DateTime,
    UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def _ahora_utc():
    return datetime.now(timezone.utc)


EstadoReserva = ENUM(
    "PENDIENTE_TRASLADO", "PENDIENTE", "PREPARADA", "ATENDIDA",
    "COMPLETADA", "CANCELADA", "VENCIDA",
    name="estado_reserva", schema="comercial", create_type=False,
)

EstadoVenta = ENUM(
    "PENDIENTE_PAGO", "PAGADA", "CANCELADA",
    "PARCIALMENTE_DEVUELTA", "DEVUELTA",
    name="estado_venta", schema="comercial", create_type=False,
)

ESTADOS_LINEA_RESERVA = (
    "PENDIENTE_TRASLADO", "RESERVADA", "RECHAZADA",
    "VENDIDA_PARCIAL", "VENDIDA", "LIBERADA",
)


class Reserva(Base):
    __tablename__ = "reservas"
    __table_args__ = (
        CheckConstraint(
            "codigo LIKE 'FS-%'",
            name="ck_reservas_codigo_formato",
        ),
        {"schema": "comercial"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.clientes.usuario_id"), nullable=False)
    sucursal_destino_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=False)
    codigo = Column(String(50), nullable=False, unique=True)
    estado = Column(EstadoReserva, nullable=False, default="PENDIENTE")
    fecha_creacion = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)
    fecha_visita = Column(DateTime(timezone=True), nullable=True)
    vence_en = Column(DateTime(timezone=True), nullable=False)
    observacion = Column(Text, nullable=True)
    # Snapshot de la politica de adelanto aplicada (RN-03 / decision 13)
    adelanto_modalidad = Column(String(20), nullable=True)
    adelanto_valor = Column(Numeric(12, 2), nullable=True)
    adelanto_monto = Column(Numeric(12, 2), nullable=True)
    # Auditoria CU10 (Entrega 4): responsable y marcas de preparacion/atencion.
    preparada_en = Column(DateTime(timezone=True), nullable=True)
    atendida_en = Column(DateTime(timezone=True), nullable=True)
    preparada_por = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=True)
    atendida_por = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=True)
    # Idempotencia (plan Ciclo 2)
    clave_idempotencia = Column(UUID(as_uuid=True), nullable=True, unique=True)
    hash_solicitud = Column(Text, nullable=True)

    detalles = relationship("DetalleReserva", back_populates="reserva", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "codigo LIKE 'FS-%'",
            name="ck_reservas_codigo_formato",
        ),
        {"schema": "comercial"},
    )


class DetalleReserva(Base):
    __tablename__ = "detalles_reserva"
    __table_args__ = (
        UniqueConstraint("reserva_id", "variante_id", name="uq_detalles_reserva_reserva_variante"),
        CheckConstraint("cantidad_solicitada > 0", name="ck_detalle_reserva_solicitada_pos"),
        CheckConstraint("cantidad_reservada >= 0", name="ck_detalle_reserva_reservada_nneg"),
        CheckConstraint("cantidad_pendiente_traslado >= 0", name="ck_detalle_reserva_pendtras_nneg"),
        CheckConstraint("cantidad_vendida >= 0", name="ck_detalle_reserva_vendida_nneg"),
        CheckConstraint("cantidad_liberada >= 0", name="ck_detalle_reserva_liberada_nneg"),
        CheckConstraint(
            "cantidad_reservada + cantidad_pendiente_traslado + cantidad_vendida + cantidad_liberada <= cantidad_solicitada",
            name="ck_detalle_reserva_cantidades_consistentes",
        ),
        {"schema": "comercial"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reserva_id = Column(
        UUID(as_uuid=True),
        ForeignKey("comercial.reservas.id", ondelete="CASCADE"),
        nullable=False,
    )
    variante_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.variantes_producto.id"), nullable=False)
    cantidad_solicitada = Column(Integer, nullable=False)
    cantidad_reservada = Column(Integer, nullable=False, default=0)
    cantidad_pendiente_traslado = Column(Integer, nullable=False, default=0)
    cantidad_vendida = Column(Integer, nullable=False, default=0)
    cantidad_liberada = Column(Integer, nullable=False, default=0)
    estado_linea = Column(String(30), nullable=False, default="RESERVADA")

    reserva = relationship("Reserva", back_populates="detalles")


class Venta(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        CheckConstraint(
            "canal IN ('PRESENCIAL','WEB','MOVIL')",
            name="ck_ventas_canal",
        ),
        CheckConstraint("subtotal >= 0", name="ck_ventas_subtotal_nneg"),
        CheckConstraint("descuento >= 0", name="ck_ventas_descuento_nneg"),
        CheckConstraint("costo_entrega >= 0", name="ck_ventas_costo_entrega_nneg"),
        CheckConstraint("total >= 0", name="ck_ventas_total_nneg"),
        CheckConstraint("adelanto_descontado >= 0", name="ck_ventas_adelanto_desc_nneg"),
        {"schema": "comercial"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero = Column(String(50), nullable=False, unique=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.clientes.usuario_id"), nullable=True)
    reserva_id = Column(UUID(as_uuid=True), ForeignKey("comercial.reservas.id"), nullable=True)
    sucursal_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=False)
    cajero_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=True)
    canal = Column(String(20), nullable=False, default="PRESENCIAL")
    estado = Column(EstadoVenta, nullable=False, default="PAGADA")
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    descuento = Column(Numeric(12, 2), nullable=False, default=0)
    costo_entrega = Column(Numeric(12, 2), nullable=False, default=0)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    creada_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)
    confirmada_en = Column(DateTime(timezone=True), nullable=True)
    # Adelanto descontado en esta venta (CU11: exactamente una vez por reserva).
    adelanto_descontado = Column(Numeric(12, 2), nullable=False, default=0)
    # Idempotencia (plan Ciclo 2)
    clave_idempotencia = Column(UUID(as_uuid=True), nullable=True, unique=True)
    hash_solicitud = Column(Text, nullable=True)

    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")


class DetalleVenta(Base):
    __tablename__ = "detalles_venta"
    __table_args__ = (
        UniqueConstraint("venta_id", "variante_id", name="uq_detalles_venta_venta_variante"),
        CheckConstraint("cantidad > 0", name="ck_detalle_venta_cantidad_pos"),
        CheckConstraint("precio_unitario >= 0", name="ck_detalle_venta_precio_nneg"),
        CheckConstraint("descuento >= 0", name="ck_detalle_venta_descuento_nneg"),
        CheckConstraint("costo_promedio >= 0", name="ck_detalle_venta_costo_nneg"),
        {"schema": "comercial"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venta_id = Column(
        UUID(as_uuid=True),
        ForeignKey("comercial.ventas.id", ondelete="CASCADE"),
        nullable=False,
    )
    detalle_reserva_id = Column(
        UUID(as_uuid=True),
        ForeignKey("comercial.detalles_reserva.id"),
        nullable=True,
    )
    variante_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.variantes_producto.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    descuento = Column(Numeric(12, 2), nullable=False, default=0)
    # Costo promedio congelado al vender (RN-09): devoluciones y margenes usan este valor.
    costo_promedio = Column(Numeric(12, 2), nullable=False, default=0)

    venta = relationship("Venta", back_populates="detalles")


class Pago(Base):
    """Pagos unificada Ciclo 2: contexto RESERVA (adelanto) o VENTA (caja).

    Columnas metodo/state superset incluyen valores de Ciclo 3
    (STRIPE_TEST, referencia_externa) listos sin crear tablas nuevas.
    """

    __tablename__ = "pagos"
    __table_args__ = (
        CheckConstraint(
            "contexto IN ('RESERVA','VENTA')",
            name="ck_pagos_contexto",
        ),
        CheckConstraint(
            "(contexto = 'RESERVA' AND reserva_id IS NOT NULL) OR "
            "(contexto = 'VENTA' AND venta_id IS NOT NULL)",
            name="ck_pagos_contexto_referencia",
        ),
        CheckConstraint(
            "metodo IN ('EFECTIVO','TARJETA_CAJA','QR_CAJA','TRANSFERENCIA','STRIPE_TEST')",
            name="ck_pagos_metodo",
        ),
        CheckConstraint("monto > 0", name="ck_pagos_monto_pos"),
        {"schema": "comercial"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contexto = Column(String(20), nullable=False)
    reserva_id = Column(UUID(as_uuid=True), ForeignKey("comercial.reservas.id"), nullable=True)
    venta_id = Column(UUID(as_uuid=True), ForeignKey("comercial.ventas.id"), nullable=True)
    metodo = Column(String(30), nullable=False)
    tipo_pago = Column(String(20), nullable=True)
    modalidad_adelanto = Column(String(20), nullable=True)
    monto = Column(Numeric(12, 2), nullable=False)
    no_reembolsable = Column(Boolean, nullable=False, default=False)
    estado = Column(String(20), nullable=False, default="PENDIENTE")
    referencia_externa = Column(String(160), nullable=True)
    proveedor_pago = Column(String(40), nullable=True)
    pagado_en = Column(DateTime(timezone=True), nullable=True)
    # Idempotencia (plan Ciclo 2)
    clave_idempotencia = Column(UUID(as_uuid=True), nullable=True, unique=True)
    hash_solicitud = Column(Text, nullable=True)
