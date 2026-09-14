"""Schemas Ciclo 2 — Devoluciones y mermas CU12 (RF22).

Devolucion reingresa al costo congelado (sin reembolso monetario).
Merma exige causa y responsable y no vuelve a disponible.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DevolucionCrearDTO(BaseModel):
    detalle_venta_id: uuid.UUID = Field(..., description="Linea de venta a devolver (parcial acumulable)")
    cantidad: int = Field(..., description="Cantidad a devolver (>0, validado en servicio -> 400)")
    motivo: Optional[str] = Field(None, description="Motivo de la devolucion")


class DevolucionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    detalle_venta_id: uuid.UUID
    venta_id: uuid.UUID
    variante_id: uuid.UUID
    sucursal_id: uuid.UUID
    cantidad: int
    costo_unitario: Decimal
    motivo: Optional[str] = None
    responsable_id: Optional[uuid.UUID] = None
    fecha_hora: datetime


class MermaCrearDTO(BaseModel):
    variante_id: uuid.UUID = Field(...)
    sucursal_id: uuid.UUID = Field(...)
    cantidad: int = Field(..., description="Cantidad mermada (>0, validado en servicio -> 400)")
    causa: Optional[str] = Field(None, description="Causa documentada (obligatoria -> 400 si falta)")
    responsable_id: Optional[uuid.UUID] = Field(None, description="Responsable (por defecto quien registra)")


class MermaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    variante_id: uuid.UUID
    sucursal_id: uuid.UUID
    cantidad: int
    costo_unitario: Decimal
    causa: Optional[str] = None
    responsable_id: Optional[uuid.UUID] = None
    fecha_hora: datetime
