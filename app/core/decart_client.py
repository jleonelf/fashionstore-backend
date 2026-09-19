"""Cliente Decart Lucy 2.5 — solo autorización segura y auditoría (CU17).

El backend no implementa cámara ni video. Emite tokens cliente de 60 s con
allowedModels=["lucy-2.5"] y constraints.realtime.maxSessionDuration=120 vía
`client.tokens.create()` (SDK oficial) o POST /v1/client/tokens. Nunca expone
la API key permanente ni registra token, Base64, video, frames, rostro, SDP o
contenido audiovisual: solo metadatos sanitizados.
"""
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

MODELO_EXCLUSIVO = "lucy-2.5"
TTL_SEGUNDOS = 60
SESION_MAX_SEGUNDOS = 120


class DecartDeshabilitado(Exception):
    pass


class DecartError(Exception):
    pass


@dataclass
class TokenClienteDecart:
    client_token: str
    expires_at: datetime
    modelo: str = MODELO_EXCLUSIVO
    max_session_duration_seconds: int = SESION_MAX_SEGUNDOS


def _habilitado() -> bool:
    return bool(settings.DECART_ENABLED and settings.DECART_API_KEY)


def parametros_token(correlation_id: str) -> dict:
    """Parámetros contractuales de `client.tokens.create()` (CU17).

    Expuestos para verificación en pruebas sin consumir créditos:
    expires_in=60, allowed_models=["lucy-2.5"],
    constraints.realtime.maxSessionDuration=120. Sin allowedOrigins (Android).
    """
    return {
        "expires_in": TTL_SEGUNDOS,
        "allowed_models": [MODELO_EXCLUSIVO],
        "constraints": {"realtime": {"maxSessionDuration": SESION_MAX_SEGUNDOS}},
        "metadata": {"correlation_id": correlation_id},
    }


async def crear_token_cliente(correlation_id: str) -> TokenClienteDecart:
    """Crea el token corto. 503 si deshabilitado/sin clave; 502 si Decart falla.

    Intenta el SDK oficial (`decart`, `client.tokens.create`); si no está
    disponible usa HTTPS directo. Nunca registra el token ni la clave.
    """
    if not _habilitado():
        raise DecartDeshabilitado("Integración Decart deshabilitada o sin clave")
    modelo = (settings.DECART_MODEL or MODELO_EXCLUSIVO).strip() or MODELO_EXCLUSIVO
    if modelo != MODELO_EXCLUSIVO:
        raise DecartError("Modelo no autorizado para CU17")
    ttl = int(settings.DECART_TOKEN_TTL_SECONDS or TTL_SEGUNDOS)
    sesion = int(settings.DECART_SESSION_MAX_SECONDS or SESION_MAX_SEGUNDOS)
    if ttl != TTL_SEGUNDOS or sesion != SESION_MAX_SEGUNDOS:
        logger.warning("Config Decart distinta del contrato (ttl=%s sesion=%s)", ttl, sesion)
        ttl, sesion = TTL_SEGUNDOS, SESION_MAX_SEGUNDOS
    # 1. SDK oficial si existe.
    try:
        from decart import DecartClient  # type: ignore

        cliente = DecartClient(api_key=settings.DECART_API_KEY)
        creador = getattr(getattr(cliente, "tokens", None), "create", None)
        if creador is not None:
            if callable(getattr(creador, "__await__", None)) or True:
                res = creador(**parametros_token(correlation_id))
                import inspect

                if inspect.isawaitable(res):
                    res = await res
                token = res.get("apiKey") if isinstance(res, dict) else getattr(res, "apiKey", None)
                if not token:
                    raise DecartError("Respuesta del SDK sin apiKey")
                logger.info("Token Decart emitido cid=%s modelo=%s", correlation_id, MODELO_EXCLUSIVO)
                return TokenClienteDecart(
                    client_token=str(token),
                    expires_at=datetime.now(timezone.utc),
                )
    except DecartError:
        raise
    except Exception as exc:  # SDK ausente o error: cae a HTTPS o 502.
        logger.info("SDK Decart no utilizable (%s); intento HTTPS", type(exc).__name__)
    # 2. HTTPS directo contra /v1/client/tokens.
    try:
        import httpx

        base = (settings.DECART_API_BASE_URL or "https://api.decart.ai").rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as cli:
            r = await cli.post(
                f"{base}/v1/client/tokens",
                headers={"x-api-key": settings.DECART_API_KEY},
                json=parametros_token(correlation_id),
            )
        if r.status_code >= 400:
            raise DecartError(f"Decart rechazó la emisión ({r.status_code})")
        data = r.json()
        token = data.get("apiKey") or data.get("client_token") or data.get("token")
        if not token:
            raise DecartError("Respuesta Decart sin token")
        logger.info("Token Decart emitido cid=%s modelo=%s", correlation_id, MODELO_EXCLUSIVO)
        return TokenClienteDecart(
            client_token=str(token),
            expires_at=datetime.now(timezone.utc),
        )
    except DecartError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"codigo": "DECART_RECHAZO", "mensaje": "El proveedor rechazó la autorización"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"codigo": "DECART_NO_DISPONIBLE", "mensaje": "Proveedor no disponible"},
        )


def autorizacion_no_disponible() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "codigo": "DECART_DESHABILITADO",
            "mensaje": "Probador virtual no configurado. Catálogo, carrito y reservas siguen operativos.",
        },
    )


# Gancho conmutable para pruebas (mock de client.tokens.create, sin créditos).
_creador_falso = None


def fijar_creador_falso(fn) -> None:
    global _creador_falso
    _creador_falso = fn


async def emitir_token(correlation_id: str) -> TokenClienteDecart:
    if _creador_falso is not None:
        token, expira = await _creador_falso(correlation_id)
        return TokenClienteDecart(client_token=str(token), expires_at=expira)
    return await crear_token_cliente(correlation_id)


def referencia_segura() -> str:
    return secrets.token_hex(8)
