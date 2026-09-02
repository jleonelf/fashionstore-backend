import uuid
from sqlalchemy import Column, String, Text, Boolean, SmallInteger, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Ciudad(Base):
    __tablename__ = "ciudades"
    __table_args__ = {"schema": "organizacion"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), nullable=False, unique=True)
    activo = Column(Boolean, nullable=False, default=True)

    sucursales = relationship("Sucursal", back_populates="ciudad")

class Sucursal(Base):
    __tablename__ = "sucursales"
    __table_args__ = (
        UniqueConstraint("ciudad_id", "nombre", name="uq_sucursales_ciudad_nombre"),
        {"schema": "organizacion"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ciudad_id = Column(UUID(as_uuid=True), ForeignKey("organizacion.ciudades.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    direccion = Column(Text, nullable=False)
    telefono = Column(String(30), nullable=True)
    numero_anillo = Column(SmallInteger, nullable=True)
    tarifa_base_delivery = Column(Numeric(12, 2), nullable=False, default=0)
    incremento_anillo_delivery = Column(Numeric(12, 2), nullable=False, default=0)
    anillo_minimo_delivery = Column(SmallInteger, nullable=False, default=1)
    anillo_maximo_delivery = Column(SmallInteger, nullable=False, default=10)
    delivery_activo = Column(Boolean, nullable=False, default=True)
    activa = Column(Boolean, nullable=False, default=True)

    ciudad = relationship("Ciudad", back_populates="sucursales")
