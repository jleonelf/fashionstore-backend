"""Schemas Ciclo 2 — Consultas CU13/CU23 (RF16, RF24).

Costos y margenes solo para roles autorizados (ADMINISTRADOR, ENCARGADO);
para el resto, costo_promedio llega en None.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.venta import VentaDTO


class HistorialComprasDTO(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[VentaDTO]


class VentaSucursalItemDTO(BaseModel):
    id: uuid.UUID
    numero: str
    creada_en: datetime
    cliente_id: Optional[uuid.UUID] = None
    reserva_id: Optional[uuid.UUID] = None
    canal: str
    estado: str
    unidades: int
    subtotal: Decimal
    descuento: Decimal
    adelanto_descontado: Decimal
    total: Decimal
    costo_total: Optional[Decimal] = Field(None, description="Solo ADMIN/ENCARGADO")
    margen_bruto: Optional[Decimal] = Field(None, description="Solo ADMIN/ENCARGADO")


class VentasSucursalResumenDTO(BaseModel):
    total_ventas: int
    unidades: int
    monto_total: Decimal
    ticket_promedio: Decimal
    costo_total: Optional[Decimal] = None
    margen_bruto_total: Optional[Decimal] = None


class VentasSucursalDTO(BaseModel):
    total: int
    limit: int
    offset: int
    resumen: VentasSucursalResumenDTO
    items: List[VentaSucursalItemDTO]
