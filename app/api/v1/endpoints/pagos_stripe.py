"""Presentación Stripe Test Mode — CU15 (RF19, RN-05)."""
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.dependencias import get_usuario_actual
from backend.app.core.idempotencia import validar_clave_idempotencia
from backend.app.models.seguridad import Usuario
from backend.app.schemas.pago_stripe import EstadoPagoDTO, IntencionCrearDTO, IntencionDTO
from backend.app.services.stripe_service import StripeService

router = APIRouter()


@router.post(
    "/stripe/intenciones", response_model=IntencionDTO, status_code=status.HTTP_201_CREATED,
    summary="Crear o reutilizar PaymentIntent (CU15)",
    description="Cliente propietario o Administrador. Una intención por venta (se reutiliza). "
    "Sin claves responde 503 tipado; la app y demás módulos siguen operativos. "
    "Requiere header Idempotency-Key.",
)
async def crearIntencion(
    datos: IntencionCrearDTO,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
    clave_idempotencia: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> IntencionDTO:
    clave = validar_clave_idempotencia(clave_idempotencia)
    dto, _ = await StripeService(db).crearIntencion(usuario, datos.venta_id, clave)
    return dto


@router.post(
    "/stripe/intenciones/reintento", response_model=IntencionDTO, status_code=status.HTTP_200_OK,
    summary="Reintentar pago dentro de la ventana (CU15)",
    description="Reutiliza la intención vigente mientras la venta siga PENDIENTE_PAGO y no expire. "
    "Vencida -> 409.",
)
async def reintentarIntencion(
    datos: IntencionCrearDTO,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
    clave_idempotencia: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> IntencionDTO:
    clave = validar_clave_idempotencia(clave_idempotencia)
    dto, _ = await StripeService(db).crearIntencion(usuario, datos.venta_id, clave)
    return dto


@router.get(
    "/stripe/estado/{venta_id}", response_model=EstadoPagoDTO,
    summary="Consultar estado de pago para polling (CU15)",
    description="El frontend consulta; nunca confirma pagos directamente.",
)
async def estadoPago(
    venta_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> EstadoPagoDTO:
    return await StripeService(db).estado(usuario, venta_id)


@router.post(
    "/stripe/webhook", status_code=status.HTTP_200_OK,
    summary="Webhook firmado de Stripe (CU15)",
    description="Única confirmación definitiva. Verifica la firma con el cuerpo HTTP crudo; "
    "firma inválida -> 400. Eventos duplicados y fuera de orden son idempotentes.",
    response_model=dict,
)
async def webhookStripe(
    request: Request,
    db: AsyncSession = Depends(get_db),
    firma: Optional[str] = Header(None, alias="Stripe-Signature"),
):
    cuerpo = await request.body()
    try:
        evento = json.loads(cuerpo.decode("utf-8") or "{}")
    except Exception:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cuerpo del webhook inválido")
    return await StripeService(db).confirmarWebhook(cuerpo, firma, evento)


@router.post(
    "/stripe/expiracion/ejecutar", status_code=status.HTTP_200_OK,
    summary="Ejecutar expiración de ventas vencidas (CU15)",
    description="Solo ADMINISTRADOR (job manual en pruebas). Advisory lock + SKIP LOCKED; "
    "cancela y libera el compromiso exactamente una vez.",
    response_model=dict,
)
async def ejecutarExpiracion(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    from backend.app.core.permisos import es_admin
    from fastapi import HTTPException

    if not es_admin(usuario):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el Administrador")
    return await StripeService(db).cancelarVencidas()
