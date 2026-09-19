"""Schemas CU22 — Promociones (RF23).

No acumulables: checkout elige el mayor descuento con desempate por ID.
Descuento nunca mayor al subtotal de línea (servicio lo topa).
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

TipoPromocion = Literal["PORCENTAJE", "MONTO_FIJO"]


class PromocionCrearDTO(BaseModel):
    codigo: str = Field(..., min_length=3, max_length=40)
    nombre: str = Field(..., min_length=3, max_length=180)
    descripcion: Optional[str] = None
    tipo: TipoPromocion
    valor: Decimal = Field(..., ge=0)
    activa: bool = True
    vigencia_inicio: Optional[datetime] = None
    vigencia_fin: Optional[datetime] = None
    variante_ids: List[uuid.UUID] = Field(default_factory=list)


class PromocionActualizarDTO(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=180)
    descripcion: Optional[str] = None
    tipo: Optional[TipoPromocion] = None
    valor: Optional[Decimal] = Field(None, ge=0)
    activa: Optional[bool] = None
    vigencia_inicio: Optional[datetime] = None
    vigencia_fin: Optional[datetime] = None


class PromocionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    tipo: str
    valor: Decimal
    activa: bool
    vigencia_inicio: Optional[datetime] = None
    vigencia_fin: Optional[datetime] = None
    creada_en: datetime
    variante_ids: List[uuid.UUID] = Field(default_factory=list)


class PromocionListaDTO(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[PromocionDTO]


class AsociarVariantesDTO(BaseModel):
    variante_ids: List[uuid.UUID] = Field(..., min_length=1)
