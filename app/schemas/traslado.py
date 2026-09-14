"""Schemas Ciclo 2 — Traslados CU09 (RF21, RF22).

Origen explicito siempre; sin seleccion automatica de sucursal.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TrasladoSolicitarDTO(BaseModel):
    detalle_reserva_id: uuid.UUID = Field(..., description="Linea RECHAZADA a reintentar (misma variante y cantidad)")
    sucursal_origen_id: uuid.UUID = Field(..., description="Origen explicito con stock suficiente")


class TrasladoRechazarDTO(BaseModel):
    motivo: Optional[str] = Field(None, description="Motivo del rechazo (opcional)")


class DetalleTrasladoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    traslado_id: uuid.UUID
    detalle_reserva_id: Optional[uuid.UUID] = None
    variante_id: uuid.UUID
    cantidad: int


class TrasladoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reserva_id: Optional[uuid.UUID] = None
    sucursal_origen_id: uuid.UUID
    sucursal_destino_id: uuid.UUID
    estado: str
    solicitado_por_id: uuid.UUID
    aprobado_por_id: Optional[uuid.UUID] = None
    fecha_solicitud: datetime
    fecha_aprobacion: Optional[datetime] = None
    fecha_despacho: Optional[datetime] = None
    fecha_recepcion: Optional[datetime] = None
    motivo_rechazo: Optional[str] = None
    detalles: List[DetalleTrasladoDTO] = Field(default_factory=list)


class TrasladoListaDTO(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[TrasladoDTO]
