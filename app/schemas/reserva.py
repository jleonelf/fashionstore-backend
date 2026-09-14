"""Schemas Ciclo 2 — Reservas CU08/CU10/CU24 (RF09-RF12).

Convencion: validacion estructural en Pydantic (422 automatico);
reglas de dominio (cantidades, duplicados, estados) en el servicio (400/409).
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class LineaReservaCrearDTO(BaseModel):
    variante_id: uuid.UUID = Field(..., description="Variante a reservar")
    cantidad: int = Field(..., description="Cantidad solicitada (>0, validado en servicio -> 400)")
    sucursal_origen_id: Optional[uuid.UUID] = Field(
        None,
        description="Origen explicito del traslado si no hay stock local (RN-02). Sin seleccion automatica.",
    )


class ReservaCrearDTO(BaseModel):
    sucursal_destino_id: uuid.UUID = Field(..., description="Sucursal donde se probara/retirara")
    fecha_visita: Optional[datetime] = Field(None, description="Fecha/hora aproximada de visita")
    observacion: Optional[str] = Field(None, description="Observacion del cliente")
    lineas: List[LineaReservaCrearDTO] = Field(..., description="Al menos una linea (validado en servicio -> 400)")


class DetalleReservaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    variante_id: uuid.UUID
    cantidad_solicitada: int
    cantidad_reservada: int
    cantidad_pendiente_traslado: int
    cantidad_vendida: int
    cantidad_liberada: int
    estado_linea: str


class TrasladoResumenDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    sucursal_origen_id: uuid.UUID
    sucursal_destino_id: uuid.UUID
    estado: str


class ReservaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cliente_id: uuid.UUID
    sucursal_destino_id: uuid.UUID
    codigo: str
    estado: str
    fecha_creacion: datetime
    fecha_visita: Optional[datetime] = None
    vence_en: datetime
    observacion: Optional[str] = None
    adelanto_modalidad: Optional[str] = None
    adelanto_valor: Optional[Decimal] = None
    adelanto_monto: Optional[Decimal] = None
    preparada_en: Optional[datetime] = None
    atendida_en: Optional[datetime] = None
    preparada_por: Optional[uuid.UUID] = None
    atendida_por: Optional[uuid.UUID] = None
    detalles: List[DetalleReservaDTO] = Field(default_factory=list)
    traslados: List[TrasladoResumenDTO] = Field(default_factory=list)


class ReservaListaDTO(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ReservaDTO]


class ExpiracionResultadoDTO(BaseModel):
    procesadas: int
    expiradas: List[str] = Field(default_factory=list, description="IDs de reservas vencidas")
    omitidas: List[str] = Field(default_factory=list, description="IDs ya terminales (idempotente)")
    errores: List[str] = Field(default_factory=list)
    bloqueo_activo: bool = Field(default=False, description="True si otra instancia tiene el advisory lock")
