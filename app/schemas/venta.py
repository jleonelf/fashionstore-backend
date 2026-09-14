"""Schemas Ciclo 2 — Venta presencial y comprobante CU11 (RF17, RF18, RF20).

Cantidades y dominio se validan en el servicio (400/409); Pydantic solo
estructura (422 automatico). Costos congelados visibles segun rol.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.pago import MetodoCaja, PagoDTO


class ItemVentaDTO(BaseModel):
    detalle_reserva_id: Optional[uuid.UUID] = Field(
        None, description="Linea de reserva (obligatorio en venta desde reserva)"
    )
    variante_id: uuid.UUID = Field(..., description="Variante vendida")
    cantidad: int = Field(..., description="Cantidad (>0, validado en servicio -> 400)")


class VentaPresencialCrearDTO(BaseModel):
    reserva_id: Optional[uuid.UUID] = Field(None, description="Reserva ATENDIDA origen (venta directa si ausente)")
    sucursal_id: uuid.UUID = Field(..., description="Sucursal y caja de la venta")
    cliente_id: Optional[uuid.UUID] = Field(None, description="Cliente (directa anonima si ausente y sin reserva)")
    metodo: MetodoCaja = Field(..., description="Unico metodo de caja por pago")
    items: List[ItemVentaDTO] = Field(..., description="Al menos un item (validado en servicio -> 400)")


class DetalleVentaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    detalle_reserva_id: Optional[uuid.UUID] = None
    variante_id: uuid.UUID
    cantidad: int
    precio_unitario: Decimal
    descuento: Decimal
    costo_promedio: Optional[Decimal] = Field(
        None, description="Costo congelado; solo roles autorizados (ADMIN/ENCARGADO)"
    )


class VentaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    numero: str
    cliente_id: Optional[uuid.UUID] = None
    reserva_id: Optional[uuid.UUID] = None
    sucursal_id: uuid.UUID
    cajero_id: Optional[uuid.UUID] = None
    canal: str
    estado: str
    subtotal: Decimal
    descuento: Decimal
    adelanto_descontado: Decimal
    costo_entrega: Decimal
    total: Decimal
    creada_en: datetime
    confirmada_en: Optional[datetime] = None
    detalles: List[DetalleVentaDTO] = Field(default_factory=list)


class ComprobanteDTO(VentaDTO):
    reserva_codigo: Optional[str] = None
    sucursal_nombre: Optional[str] = None
    cajero_nombre: Optional[str] = None
    pagos: List[PagoDTO] = Field(default_factory=list)
