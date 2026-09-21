"""Controller ProbadorService — CU17 (RF13) con Decart Lucy 2.5 Realtime.

Solo compatibilidad, autorización segura y auditoría sanitizada. Modelo
exclusivo lucy-2.5, token de 60 s, allowedModels=["lucy-2.5"],
constraints.realtime.maxSessionDuration=120. Valida cliente autenticado,
variante activa y compatible (solo prendas superiores del catálogo), imagen
HTTPS de origen permitido (JPEG/PNG/WebP) y consentimiento decart-v1. Aplica
idempotencia y rate limit; omite allowedOrigins (Android); nunca devuelve la
API key ni registra token/Base64/video/frames/rostro/SDP. Sin fallback local.
"""
import uuid
from datetime import timedelta
from typing import Tuple
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core import decart_client
from backend.app.core import idempotencia_ciclo3 as idem3
from backend.app.core import rate_limit
from backend.app.core.config import settings
from backend.app.core.idempotencia import hash_payload
from backend.app.core.permisos import rol_de
from backend.app.core.reloj import RelojSistema
from backend.app.models.ciclo3 import HistorialNavegacion
from backend.app.models.seguridad import Usuario
from backend.app.repositories.ciclo3_repository import NavegacionRepository
from backend.app.repositories.variante_repository import VarianteRepository
from backend.app.schemas.probador_ia import (
    CONSENTIMIENTO_VIGENTE, AutorizacionCrearDTO, AutorizacionDTO, PruebaVirtualDTO,
)

# Prendas superiores habilitadas por el proyecto (compatibilidad CU17).
CATEGORIAS_SUPERIORES = frozenset({
    "CAMISA", "CAMISAS", "BLUSA", "BLUSAS", "POLERA", "POLERAS", "REMERA",
    "CHAQUETA", "CHAMARRA", "SACO", "ABRIGO", "CHALECO", "SUDADERA", "TOP",
    "BLAZER", "BLAZERS",
})
PROMPT_PRENDA = (
    "Replace only the current top with the referenced garment, preserving its "
    "color, silhouette, print, logo and fabric details. Keep the person's pose "
    "and background unchanged. Photorealistic, no size advice."
)


def _origenes_permitidos() -> list:
    from backend.app.core.decart_imagen import origenes_permitidos as _ops

    return _ops()


async def validar_imagen_prenda(url: str) -> None:
    """Validación segura delegada al adaptador inyectable (sin red en pruebas).

    Sintaxis + contenido: HTTPS, allowlist obligatoria cuando la integración
    está habilitada, sin destinos internos, sin redirecciones inseguras,
    JPEG/PNG/WebP real, tamaño limitado, 512×512 mínimo, timeout, sin
    almacenar bytes ni registrar URL firmada/contenido/Base64.
    """
    from backend.app.core.decart_imagen import obtener_validador

    await obtener_validador().validar(url)


def validar_imagen_prenda_sync(url: str) -> None:
    """Compatibilidad: validación sintáctica sin red (no usar en flujo)."""
    from backend.app.core.decart_imagen import validar_sintaxis

    validar_sintaxis(url)


class ProbadorService:
    def __init__(self, db: AsyncSession, reloj=None):
        self.db = db
        self.reloj = reloj or RelojSistema()
        self.variante_repo = VarianteRepository(db)
        self.navegacion_repo = NavegacionRepository(db)

    async def _variante_compatible(self, variante_id: uuid.UUID):
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from backend.app.models.catalogo import Producto, VarianteProducto

        q = (
            select(VarianteProducto)
            .options(
                selectinload(VarianteProducto.producto).selectinload(Producto.categoria),
                selectinload(VarianteProducto.producto).selectinload(Producto.imagenes),
            )
            .where(VarianteProducto.id == variante_id)
        )
        variante = (await self.db.execute(q)).scalars().first()
        if variante is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada")
        if not variante.activa:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Variante inactiva")
        producto = variante.producto
        if producto is None or not producto.activo:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Producto no disponible")
        categoria = (producto.categoria.nombre.upper()
                     if producto.categoria and producto.categoria.nombre else "")
        if not any(c in categoria for c in CATEGORIAS_SUPERIORES):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Variante incompatible con el probador (solo prendas superiores)",
            )
        recurso = (variante.recurso_prueba_virtual or "").strip()
        if not recurso:
            # Contrato móvil CU17: si la variante no tiene un recurso propio,
            # Decart utiliza exclusivamente la primera foto real del producto.
            # La principal ocupa la primera posición; luego se respeta `orden`.
            imagenes = sorted(
                producto.imagenes or [],
                key=lambda img: (not bool(img.es_principal), img.orden, str(img.id)),
            )
            if imagenes:
                recurso = (imagenes[0].enlace_imagen or "").strip()
        if not recurso:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Variante sin una primera imagen compatible con el probador",
            )
        # Imagen frontal/recurso de catálogo: validación segura inyectable
        # (HTTPS, allowlist, sin internos, sin redirecciones inseguras,
        # JPEG/PNG/WebP real, tamaño y 512×512, timeout; sin guardar bytes).
        await validar_imagen_prenda(recurso)
        return variante, producto, recurso

    async def recursoPrueba(self, usuario: Usuario, variante_id: uuid.UUID) -> PruebaVirtualDTO:
        if rol_de(usuario) != "CLIENTE":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el Cliente usa el probador")
        variante, _, recurso = await self._variante_compatible(variante_id)
        return PruebaVirtualDTO(
            variante_id=variante.id, compatible=True,
            imagen_prenda_url=recurso, prompt_prenda=PROMPT_PRENDA,
        )

    async def autorizar(
        self, usuario: Usuario, dto: AutorizacionCrearDTO, clave: uuid.UUID,
    ) -> Tuple[AutorizacionDTO, bool]:
        if rol_de(usuario) != "CLIENTE":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el Cliente usa el probador")
        if dto.consentimiento_version != CONSENTIMIENTO_VIGENTE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Versión de consentimiento inválida",
            )
        rate_limit.verificar_limite(
            f"decart:{usuario.id}", settings.DECART_RATE_LIMIT_POR_MINUTO or 10, 60
        )
        digest = hash_payload(dto.model_dump(mode="json"))
        try:
            previo = await idem3.reclamar(
                self.db, clave, digest, recurso_tipo="PROBADOR",
                operacion="AUTORIZAR", usuario_id=usuario.id, ttl_horas=1,
            )
            if previo is not None and previo.respuesta:
                # Ámbito ya aislado por usuario: nunca devolver a otro
                # usuario un token almacenado. Misma clave + payload
                # devuelve el mismo resultado vigente; si el token ya
                # expiró se emite uno nuevo (no se reusa).
                try:
                    from datetime import datetime as _dt

                    exp = _dt.fromisoformat(str(previo.respuesta.get("expires_at", "")))
                    if exp.tzinfo is None:
                        from datetime import timezone as _tz

                        exp = exp.replace(tzinfo=_tz.utc)
                    if exp > self.reloj.ahora():
                        dto_previo = AutorizacionDTO(**previo.respuesta)
                        return dto_previo, False
                except Exception:
                    dto_previo = AutorizacionDTO(**previo.respuesta)
                    return dto_previo, False
                await self.db.delete(previo)
                await self.db.flush()
            variante, _, recurso = await self._variante_compatible(dto.variante_id)
            if not settings.DECART_ENABLED or not settings.DECART_API_KEY:
                raise decart_client.autorizacion_no_disponible()
            try:
                token = await decart_client.emitir_token(f"probador-{clave}")
            except decart_client.DecartDeshabilitado:
                raise decart_client.autorizacion_no_disponible()
            except decart_client.DecartError:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"codigo": "DECART_RECHAZO",
                            "mensaje": "El proveedor rechazó la autorización"},
                )
            except HTTPException:
                raise
            # Usar expires_at real del proveedor cuando esté disponible.
            expira = getattr(token, "expires_at", None)
            try:
                if expira is None:
                    raise ValueError("sin expira")
                if expira.tzinfo is None:
                    from datetime import timezone as _tz

                    expira = expira.replace(tzinfo=_tz.utc)
            except Exception:
                expira = self.reloj.ahora() + timedelta(seconds=decart_client.TTL_SEGUNDOS)
            salida = AutorizacionDTO(
                client_token=token.client_token, expires_at=expira,
                modelo=decart_client.MODELO_EXCLUSIVO,
                max_session_duration_seconds=decart_client.SESION_MAX_SEGUNDOS,
                imagen_prenda_url=recurso, prompt_prenda=PROMPT_PRENDA,
            )
            # Auditoría sanitizada: sin token ni contenido audiovisual.
            self.db.add(
                HistorialNavegacion(
                    cliente_id=usuario.id, usuario_id=usuario.id,
                    variante_id=variante.id, producto_id=variante.producto_id,
                    evento="PRUEBA_VIRTUAL",
                    metadatos={
                        "modelo": decart_client.MODELO_EXCLUSIVO,
                        "consentimiento": CONSENTIMIENTO_VIGENTE,
                    },
                )
            )
            await self.db.flush()
            # No guardar el token en la respuesta idempotente más allá de su TTL:
            # se cachea solo dentro de la ventana de 60 s y en el ámbito del
            # usuario (nunca se comparte entre clientes).
            await idem3.guardar_respuesta(
                self.db, clave, salida.model_dump(mode="json"),
                usuario_id=usuario.id, recurso_tipo="PROBADOR",
                operacion="AUTORIZAR",
            )
            await self.db.commit()
            return salida, True
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise
