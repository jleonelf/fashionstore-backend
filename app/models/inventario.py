import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Numeric, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class LoteRecepcion(Base):
    __tablename__ = "lotes_recepcion"
    __table_args__ = {"schema": "inventario"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proveedor_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.proveedores.id"), nullable=False)
    sucursal_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=False)
    temporada_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.temporadas.id"), nullable=True)
    coleccion_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.colecciones.id"), nullable=True)
    recibido_por_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=False)
    numero_documento = Column(String(100), nullable=True)
    fecha_recepcion = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    observacion = Column(Text, nullable=True)

    detalles = relationship("DetalleLoteRecepcion", back_populates="lote", cascade="all, delete-orphan")

class DetalleLoteRecepcion(Base):
    __tablename__ = "detalles_lote_recepcion"
    __table_args__ = (
        UniqueConstraint("lote_id", "variante_id", name="uq_detalles_lote_variante"),
        {"schema": "inventario"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lote_id = Column(UUID(as_uuid=True), ForeignKey("inventario.lotes_recepcion.id", ondelete="CASCADE"), nullable=False)
    variante_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.variantes_producto.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(12, 2), nullable=False)

    lote = relationship("LoteRecepcion", back_populates="detalles")

class InventarioSucursal(Base):
    __tablename__ = "inventario_sucursal"
    __table_args__ = (
        UniqueConstraint("variante_id", "sucursal_id", name="uq_inventario_variante_sucursal"),
        {"schema": "inventario"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variante_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.variantes_producto.id"), nullable=False)
    sucursal_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=False)
    disponible = Column(Integer, nullable=False, default=0)
    reservado = Column(Integer, nullable=False, default=0)
    comprometido_traslado = Column(Integer, nullable=False, default=0)
    en_transito = Column(Integer, nullable=False, default=0)
    actualizado_en = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    __table_args__ = {"schema": "inventario"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variante_id = Column(UUID(as_uuid=True), ForeignKey("catalogo.variantes_producto.id"), nullable=False)
    sucursal_origen_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=True)
    sucursal_destino_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.sucursales.id"), nullable=True)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("seguridad.usuarios.id"), nullable=True)
    tipo = Column(String(40), nullable=False)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(12, 2), nullable=False, default=0)
    referencia_tipo = Column(String(40), nullable=True)
    referencia_id = Column(UUID(as_uuid=True), nullable=True)
    fecha_hora = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    observacion = Column(Text, nullable=True)
