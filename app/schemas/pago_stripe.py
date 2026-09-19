"""Schemas CU15 — Stripe Test Mode (RF19) y CU16 — Entregas.

Solo IDs/referencias y estados; nunca tarjeta/CVC. Webhook firmado es la única
confirmación definitiva; el cliente nunca confirma pagos directamente.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

EstadoPagoStripe = Literal["PENDIENTE", "APROBADO", "RECHAZADO", "ANULADO"]
ModalidadEntrega = Literal["RECOJO", "DELIVERY"]


class IntencionCrearDTO(BaseModel):
    venta_id: uuid.UUID = Field(..., description="Venta PENDIENTE_PAGO del checkout digital")


class IntencionDTO(BaseModel):
    payment_intent_id: str
    venta_id: uuid.UUID
    monto: Decimal
    moneda: str
    estado: str
    client_secret: Optional[str] = None


class EstadoPagoDTO(BaseModel):
    venta_id: uuid.UUID
    estado_venta: str
    estado_pago: str
    payment_intent_id: Optional[str] = None
    monto: Decimal
    expira_en: Optional[datetime] = None


class CotizacionDTO(BaseModel):
    sucursal_id: uuid.UUID
    anillo_sucursal: Optional[int] = None
    anillo_destino: int
    tarifa_base: Decimal
    incremento_anillo: Decimal
    costo_entrega: Decimal


class PedidoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    venta_id: uuid.UUID
    sucursal_id: uuid.UUID
    modalidad: str
    estado: str
    anillo_sucursal: Optional[int] = None
    anillo_destino: Optional[int] = None
    direccion: Optional[str] = None
    tarifa_base: Decimal
    incremento_anillo: Decimal
    costo_entrega: Decimal
    codigo_recojo: Optional[str] = None
    creada_en: datetime


class PedidoListaDTO(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[PedidoDTO]


class TransicionPedidoDTO(BaseModel):
    estado: Literal[
        "SOLICITADO", "PREPARADO", "LISTO_RECOJO", "EN_REPARTO",
        "RECOGIDO", "ENTREGADO", "CANCELADO",
    ]
