"""Schemas CU14 — Carrito y checkout (RF14, RF15, RF16).

Carrito activo aislado por cliente; agregar no compromete inventario; el
checkout usa una sola sucursal y crea venta PENDIENTE_PAGO con compromiso de
60 minutos. Importes con Decimal.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

CanalDigital = Literal["WEB", "MOVIL"]
ModalidadEntrega = Literal["RECOJO", "DELIVERY"]


class LineaAgregarDTO(BaseModel):
    variante_id: uuid.UUID
    cantidad: int = Field(..., gt=0, le=99)


class LineaActualizarDTO(BaseModel):
    cantidad: int = Field(..., gt=0, le=99)


class LineaCarritoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    variante_id: uuid.UUID
    cantidad: int
    precio_unitario: Decimal = Decimal("0")
    descuento_unitario: Decimal = Decimal("0")
    promocion_id: Optional[uuid.UUID] = None
    subtotal: Decimal = Decimal("0")


class CarritoDTO(BaseModel):
    id: uuid.UUID
    cliente_id: uuid.UUID
    canal: str
    estado: str
    creada_en: datetime
    actualizada_en: datetime
    lineas: List[LineaCarritoDTO] = Field(default_factory=list)
    subtotal: Decimal = Decimal("0")
    descuento_total: Decimal = Decimal("0")
    total: Decimal = Decimal("0")


class CoberturaSucursalDTO(BaseModel):
    sucursal_id: uuid.UUID
    sucursal_nombre: str
    cubre_todo: bool
    faltantes: List[uuid.UUID] = Field(default_factory=list)


class CoberturaDTO(BaseModel):
    sucursales: List[CoberturaSucursalDTO]


class CheckoutCrearDTO(BaseModel):
    sucursal_id: uuid.UUID = Field(..., description="Única sucursal de origen del inventario")
    canal: CanalDigital = Field(..., description="WEB o MOVIL")
    modalidad: ModalidadEntrega = Field(..., description="RECOJO o DELIVERY")
    direccion: Optional[str] = Field(None, description="Obligatoria en DELIVERY")
    anillo_destino: Optional[int] = Field(None, ge=1, le=12)


class CheckoutRespuestaDTO(BaseModel):
    venta_id: uuid.UUID
    numero: str
    estado: str
    total: Decimal
    expira_en: datetime
    pedido_entrega_id: uuid.UUID
