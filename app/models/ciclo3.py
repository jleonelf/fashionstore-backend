"""Modelos Ciclo 3 — carrito/checkout, promociones, entregas, IA y probador (CU14-CU22, CU25).

Alineados con docu_general/ciclo-3/01-plan-datos-infra-ciclo3.md y el banner
CICLO 3 del SQL. No toca tablas de Ciclos 1-2 salvo columnas auxiliares
documentadas (ventas.expira_en, detalles_venta.promocion_id); ver migración
0004_ciclo3_backend.py. Todo importe con Decimal en servicios; aquí solo DDL.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer,
    Numeric, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def _ahora_utc():
    return datetime.now(timezone.utc)


class Promocion(Base):
    """catalogo.promociones — CU22. Tipo PORCENTAJE (0-100) o MONTO_FIJO."""

    __tablename__ = "promociones"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('PORCENTAJE','MONTO_FIJO')",
            name="ck_promociones_tipo",
        ),
        CheckConstraint("valor >= 0", name="ck_promociones_valor_nneg"),
        CheckConstraint(
            "(tipo <> 'PORCENTAJE') OR (valor <= 100)",
            name="ck_promociones_porcentaje_max",
        ),
        CheckConstraint(
            "vigencia_fin IS NULL OR vigencia_inicio IS NULL OR vigencia_inicio <= vigencia_fin",
            name="ck_promociones_vigencia_coherente",
        ),
        {"schema": "catalogo"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(40), nullable=False, unique=True)
    nombre = Column(String(180), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(20), nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)
    activa = Column(Boolean, nullable=False, default=True)
    vigencia_inicio = Column(DateTime(timezone=True), nullable=True)
    vigencia_fin = Column(DateTime(timezone=True), nullable=True)
    creada_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)
    actualizada_en = Column(
        DateTime(timezone=True), default=_ahora_utc, onupdate=_ahora_utc, nullable=False
    )
    creada_por = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=True)

    variantes = relationship(
        "PromocionVariante", back_populates="promocion", cascade="all, delete-orphan"
    )


class PromocionVariante(Base):
    """catalogo.promocion_variante — asociación promo <-> variante (CU22)."""

    __tablename__ = "promocion_variante"
    __table_args__ = {"schema": "catalogo"}

    promocion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogo.promociones.id", ondelete="CASCADE"),
        primary_key=True,
    )
    variante_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogo.variantes_producto.id", ondelete="CASCADE"),
        primary_key=True,
    )
    creada_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)

    promocion = relationship("Promocion", back_populates="variantes")


class Carrito(Base):
    """comercial.carritos — un ACTIVO por (cliente, canal); canal WEB|MOVIL."""

    __tablename__ = "carritos"
    __table_args__ = (
        CheckConstraint(
            "canal IN ('WEB','MOVIL')",
            name="ck_carritos_canal",
        ),
        CheckConstraint(
            "estado IN ('ACTIVO','CONVERTIDO','ABANDONADO')",
            name="ck_carritos_estado",
        ),
        Index(
            "uq_carritos_activo_por_cliente_canal",
            "cliente_id", "canal",
            unique=True,
            postgresql_where="estado = 'ACTIVO'",
        ),
        Index("idx_carritos_cliente_estado", "cliente_id", "estado"),
        {"schema": "comercial"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(
        UUID(as_uuid=True), ForeignKey("seguridad.clientes.usuario_id"), nullable=False
    )
    canal = Column(String(10), nullable=False, default="WEB")
    estado = Column(String(20), nullable=False, default="ACTIVO")
    creada_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)
    actualizada_en = Column(
        DateTime(timezone=True), default=_ahora_utc, onupdate=_ahora_utc, nullable=False
    )
    convertida_en = Column(DateTime(timezone=True), nullable=True)
    venta_id = Column(UUID(as_uuid=True), ForeignKey("comercial.ventas.id"), nullable=True)

    lineas = relationship(
        "DetalleCarrito", back_populates="carrito", cascade="all, delete-orphan"
    )


class DetalleCarrito(Base):
    """comercial.detalles_carrito — una fila por variante en el carrito."""

    __tablename__ = "detalles_carrito"
    __table_args__ = (
        UniqueConstraint("carrito_id", "variante_id", name="uq_detalle_carrito_carrito_variante"),
        CheckConstraint("cantidad > 0", name="ck_detalle_carrito_cantidad_pos"),
        Index("idx_detalle_carrito_carrito", "carrito_id"),
        {"schema": "comercial"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carrito_id = Column(
        UUID(as_uuid=True),
        ForeignKey("comercial.carritos.id", ondelete="CASCADE"),
        nullable=False,
    )
    variante_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogo.variantes_producto.id"),
        nullable=False,
    )
    cantidad = Column(Integer, nullable=False)
    agregado_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)
    actualizado_en = Column(
        DateTime(timezone=True), default=_ahora_utc, onupdate=_ahora_utc, nullable=False
    )

    carrito = relationship("Carrito", back_populates="lineas")


class PedidoEntrega(Base):
    """comercial.pedidos_entrega — 1:1 con la venta digital (CU16).

    Congela sucursal, anillos, parámetros, dirección y costo final.
    RECOJO: costo 0 y sin dirección de delivery. DELIVERY: exige dirección y
    anillo dentro del snapshot permitido.
    """

    __tablename__ = "pedidos_entrega"
    __table_args__ = (
        CheckConstraint(
            "modalidad IN ('RECOJO','DELIVERY')",
            name="ck_pedidos_modalidad",
        ),
        CheckConstraint(
            "(modalidad = 'RECOJO') OR (direccion IS NOT NULL AND anillo_destino IS NOT NULL)",
            name="ck_pedidos_delivery_requiere_datos",
        ),
        CheckConstraint(
            "(modalidad = 'DELIVERY') OR (costo_entrega = 0)",
            name="ck_pedidos_recojo_sin_tarifa",
        ),
        CheckConstraint("costo_entrega >= 0", name="ck_pedidos_costo_nneg"),
        CheckConstraint("tarifa_base >= 0", name="ck_pedidos_tarifa_nneg"),
        CheckConstraint("incremento_anillo >= 0", name="ck_pedidos_incremento_nneg"),
        Index("idx_pedidos_sucursal_estado", "sucursal_id", "estado"),
        Index("idx_pedidos_venta", "venta_id"),
        {"schema": "comercial"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venta_id = Column(
        UUID(as_uuid=True), ForeignKey("comercial.ventas.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    sucursal_id = Column(
        UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=False
    )
    cliente_id = Column(
        UUID(as_uuid=True), ForeignKey("seguridad.clientes.usuario_id"), nullable=False
    )
    modalidad = Column(String(20), nullable=False)
    estado = Column(String(20), nullable=False, default="SOLICITADO")
    anillo_sucursal = Column(SmallInteger, nullable=True)
    anillo_destino = Column(SmallInteger, nullable=True)
    anillo_minimo = Column(SmallInteger, nullable=True)
    anillo_maximo = Column(SmallInteger, nullable=True)
    direccion = Column(Text, nullable=True)
    tarifa_base = Column(Numeric(12, 2), nullable=False, default=0)
    incremento_anillo = Column(Numeric(12, 2), nullable=False, default=0)
    costo_entrega = Column(Numeric(12, 2), nullable=False, default=0)
    codigo_recojo = Column(String(20), nullable=True)
    creada_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)
    actualizada_en = Column(
        DateTime(timezone=True), default=_ahora_utc, onupdate=_ahora_utc, nullable=False
    )


class HistorialNavegacion(Base):
    """inteligencia.historial_navegacion — eventos incl. PRUEBA_VIRTUAL (CU17/CU18).

    Sanitizado: nunca token, Base64, video, frames, rostro ni SDP.
    """

    __tablename__ = "historial_navegacion"
    __table_args__ = (
        Index("idx_navegacion_cliente_fecha", "cliente_id", "creada_en"),
        Index("idx_navegacion_evento", "evento"),
        {"schema": "inteligencia"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(
        UUID(as_uuid=True), ForeignKey("seguridad.clientes.usuario_id"), nullable=True
    )
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=True)
    variante_id = Column(
        UUID(as_uuid=True), ForeignKey("catalogo.variantes_producto.id"), nullable=True
    )
    producto_id = Column(
        UUID(as_uuid=True), ForeignKey("catalogo.productos.id"), nullable=True
    )
    evento = Column(String(40), nullable=False)
    metadatos = Column(JSONB, nullable=False, default=dict)
    creada_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)


class SolicitudIA(Base):
    """inteligencia.solicitudes_ia — auditoría de IA con respuesta y datos (CU18/20/21/25)."""

    __tablename__ = "solicitudes_ia"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('RECOMENDACION','BUSQUEDA_VOZ','REPORTE','DECISION_INVENTARIO')",
            name="ck_solicitudes_ia_tipo",
        ),
        Index("idx_solicitudes_tipo_fecha", "tipo", "creada_en"),
        Index("idx_solicitudes_usuario", "usuario_id"),
        {"schema": "inteligencia"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=True)
    cliente_id = Column(
        UUID(as_uuid=True), ForeignKey("seguridad.clientes.usuario_id"), nullable=True
    )
    tipo = Column(String(30), nullable=False)
    entrada = Column(Text, nullable=False, default="")
    funcion_usada = Column(String(60), nullable=True)
    parametros = Column(JSONB, nullable=False, default=dict)
    respuesta = Column(Text, nullable=False, default="")
    datos = Column(JSONB, nullable=False, default=dict)
    proveedor = Column(String(20), nullable=False, default="DETERMINISTA")
    latencia_ms = Column(Integer, nullable=False, default=0)
    creada_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)


class RegistroIdempotencia(Base):
    """comercial.registros_idempotencia — idempotencia genérica Ciclo 3.

    Cubre operaciones sin columna propia (líneas de carrito, autorizaciones
    Decart, cotizaciones auditadas): misma clave + mismo hash -> respuesta
    original; misma clave + distinto hash -> 409. Las ventas/pagos ya tienen
    su propia clave_idempotencia y no usan esta tabla.
    """

    __tablename__ = "registros_idempotencia"
    __table_args__ = (
        Index("idx_idempotencia_expira", "expira_en"),
        {"schema": "comercial"},
    )

    clave = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hash_solicitud = Column(Text, nullable=False)
    recurso_tipo = Column(String(40), nullable=False)
    recurso_id = Column(UUID(as_uuid=True), nullable=True)
    respuesta = Column(JSONB, nullable=False, default=dict)
    creada_en = Column(DateTime(timezone=True), default=_ahora_utc, nullable=False)
    expira_en = Column(DateTime(timezone=True), nullable=True)
