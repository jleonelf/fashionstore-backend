"""Presentación Probador Decart — CU17 (RF13) + navegación sanitizada."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.dependencias import get_usuario_actual
from backend.app.core.idempotencia import validar_clave_idempotencia
from backend.app.models.seguridad import Usuario
from backend.app.schemas.probador_ia import (
    AutorizacionCrearDTO, AutorizacionDTO, NavegacionCrearDTO, PruebaVirtualDTO,
)
from backend.app.services.probador_service import ProbadorService

router = APIRouter()


@router.get(
    "/variantes/{variante_id}/prueba-virtual", response_model=PruebaVirtualDTO,
    summary="Compatibilidad y recurso de prueba virtual (CU17)",
    description="Cliente autenticado. Valida variante activa y compatible (solo prendas superiores), "
    "imagen HTTPS de origen permitido (JPEG/PNG/WebP) y prompt controlado por catálogo. "
    "Nunca garantiza talla.",
)
async def recursoPruebaVirtual(
    variante_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> PruebaVirtualDTO:
    return await ProbadorService(db).recursoPrueba(usuario, variante_id)


@router.post(
    "/probador/autorizaciones", response_model=AutorizacionDTO, status_code=status.HTTP_201_CREATED,
    summary="Autorizar sesión Decart Lucy 2.5 (CU17)",
    description="Token cliente de 60 s, allowedModels=['lucy-2.5'], maxSessionDuration=120. "
    "Requiere consentimiento 'decart-v1', Idempotency-Key y respeta rate limit (429). "
    "Sin clave responde 503 tipado. Nunca devuelve la API key permanente ni registra "
    "token, Base64, video, frames, rostro, SDP ni contenido audiovisual.",
)
async def crearAutorizacion(
    datos: AutorizacionCrearDTO,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
    clave_idempotencia: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> AutorizacionDTO:
    clave = validar_clave_idempotencia(clave_idempotencia)
    dto, _ = await ProbadorService(db).autorizar(usuario, datos, clave)
    return dto
