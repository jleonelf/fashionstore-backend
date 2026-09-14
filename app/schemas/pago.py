"""Schemas Ciclo 2 — Pagos y adelantos (RN-03, CU11).

Metodos de caja: EFECTIVO, TARJETA_CAJA, QR_CAJA, TRANSFERENCIA.
STRIPE_TEST queda reservado a Ciclo 3 (solo existe como valor permitido).
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

MetodoCaja = Literal["EFECTIVO", "TARJETA_CAJA", "QR_CAJA", "TRANSFERENCIA"]


class AdelantoCrearDTO(BaseModel):
    reserva_id: uuid.UUID = Field(..., description="Reserva sobre la que se registra el adelanto")
    metodo: MetodoCaja = Field(..., description="Unico metodo de caja por pago")


class PagoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contexto: str
    reserva_id: Optional[uuid.UUID] = None
    venta_id: Optional[uuid.UUID] = None
    metodo: str
    tipo_pago: Optional[str] = None
    modalidad_adelanto: Optional[str] = None
    monto: Decimal
    no_reembolsable: bool
    estado: str
    referencia_externa: Optional[str] = None
    pagado_en: Optional[datetime] = None
    clave_idempotencia: Optional[uuid.UUID] = None


class PagoListaDTO(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[PagoDTO]
