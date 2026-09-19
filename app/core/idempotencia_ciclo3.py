"""Idempotencia genérica Ciclo 3 sobre comercial.registros_idempotencia.

Ventas/pagos conservan su propia clave_idempotencia (Ciclo 2). Esta tabla cubre
operaciones sin columna propia: mutaciones de carrito y autorizaciones Decart.
Misma clave + mismo hash -> respuesta original; distinta -> 409.
"""
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ciclo3 import RegistroIdempotencia


def hash_payload(payload: Any) -> str:
    canonico = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


async def reclamar(
    db: AsyncSession,
    clave: uuid.UUID,
    hash_solicitud: str,
    recurso_tipo: str,
    ttl_horas: int = 24,
) -> Optional[RegistroIdempotencia]:
    """Reserva la clave o devuelve el registro previo.

    - Sin registro -> crea marcador con respuesta {} y retorna None (el servicio
      continúa y luego guarda la respuesta con `guardar_respuesta`).
    - Mismo hash -> retorna el registro (reintento seguro).
    - Distinto hash -> 409.
    """
    existente = await db.get(RegistroIdempotencia, clave)
    if existente is None:
        marcador = RegistroIdempotencia(
            clave=clave, hash_solicitud=hash_solicitud, recurso_tipo=recurso_tipo,
            respuesta={},
            expira_en=datetime.now(timezone.utc) + timedelta(hours=ttl_horas),
        )
        db.add(marcador)
        await db.flush()
        return None
    if existente.hash_solicitud != hash_solicitud:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key ya usada con otra solicitud",
        )
    return existente


async def guardar_respuesta(
    db: AsyncSession, clave: uuid.UUID, respuesta: dict,
    recurso_id: Optional[uuid.UUID] = None,
) -> None:
    registro = await db.get(RegistroIdempotencia, clave)
    if registro is not None:
        registro.respuesta = respuesta
        if recurso_id is not None:
            registro.recurso_id = recurso_id
        await db.flush()
