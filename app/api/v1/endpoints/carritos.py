"""Presentación Carrito y checkout — CU14 (RF14, RF15, RF16)."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.dependencias import get_usuario_actual
from backend.app.core.idempotencia import validar_clave_idempotencia
from backend.app.models.seguridad import Usuario
from backend.app.schemas.carrito import (
    CarritoDTO, CheckoutCrearDTO, CheckoutRespuestaDTO, CoberturaDTO,
    LineaActualizarDTO, LineaAgregarDTO,
)
from backend.app.services.carrito_service import CarritoService

router = APIRouter()
CANALES = ("WEB", "MOVIL")


def _canal(canal: str) -> str:
    c = (canal or "WEB").upper()
    if c not in CANALES:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Canal inválido: WEB o MOVIL")
    return c


@router.get(
    "/mio", response_model=CarritoDTO, summary="Obtener mi carrito activo (CU14)",
    description="Cliente propietario. Crea el carrito ACTIVO si no existe. "
    "Muestra promoción vigente estimada por línea (se congela en el checkout).",
)
async def obtenerMiCarrito(
    canal: str = Query("WEB", description="WEB o MOVIL"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> CarritoDTO:
    return await CarritoService(db).obtener_mio(usuario, _canal(canal))


@router.post(
    "/mio/lineas", response_model=CarritoDTO, status_code=status.HTTP_200_OK,
    summary="Agregar línea al carrito (CU14)",
    description="Idempotente (header Idempotency-Key obligatorio). Agregar no compromete inventario. "
    "Revalida variante activa.",
)
async def agregarLinea(
    datos: LineaAgregarDTO,
    canal: str = Query("WEB"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
    clave_idempotencia: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> CarritoDTO:
    clave = validar_clave_idempotencia(clave_idempotencia)
    dto, _ = await CarritoService(db).agregar(usuario, datos, _canal(canal), clave)
    return dto


@router.patch(
    "/mio/lineas/{variante_id}", response_model=CarritoDTO, summary="Modificar cantidad (CU14)",
    description="Idempotente (header Idempotency-Key obligatorio).",
)
async def modificarLinea(
    variante_id: uuid.UUID,
    datos: LineaActualizarDTO,
    canal: str = Query("WEB"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
    clave_idempotencia: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> CarritoDTO:
    clave = validar_clave_idempotencia(clave_idempotencia)
    dto, _ = await CarritoService(db).modificar(usuario, variante_id, datos, _canal(canal), clave)
    return dto


@router.delete(
    "/mio/lineas/{variante_id}", response_model=CarritoDTO, summary="Quitar línea (CU14)",
    description="Idempotente (header Idempotency-Key obligatorio).",
)
async def quitarLinea(
    variante_id: uuid.UUID,
    canal: str = Query("WEB"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
    clave_idempotencia: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> CarritoDTO:
    clave = validar_clave_idempotencia(clave_idempotencia)
    dto, _ = await CarritoService(db).quitar(usuario, variante_id, _canal(canal), clave)
    return dto


@router.delete(
    "/mio", response_model=CarritoDTO, summary="Vaciar carrito (CU14)",
    description="Idempotente (header Idempotency-Key obligatorio).",
)
async def vaciarCarrito(
    canal: str = Query("WEB"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
    clave_idempotencia: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> CarritoDTO:
    clave = validar_clave_idempotencia(clave_idempotencia)
    dto, _ = await CarritoService(db).vaciar(usuario, _canal(canal), clave)
    return dto


@router.get(
    "/mio/cobertura", response_model=CoberturaDTO, summary="Sucursales que cubren el carrito (CU14)",
    description="Solo lectura, sin bloqueo ni reserva. Ordena primero las que cubren todo.",
)
async def coberturaCarrito(
    canal: str = Query("WEB"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> CoberturaDTO:
    return await CarritoService(db).cobertura(usuario, _canal(canal))


@router.post(
    "/mio/checkout", response_model=CheckoutRespuestaDTO, status_code=status.HTTP_201_CREATED,
    summary="Confirmar compra digital (CU14)",
    description="Canal WEB o MOVIL, modalidad RECOJO o DELIVERY, una sola sucursal. Crea venta "
    "PENDIENTE_PAGO, compromete stock 60 min (SELECT FOR UPDATE ordenado + Kardex), congela "
    "precio/descuento/promoción/costo/tarifa y crea el pedido SOLICITADO. Si ninguna sucursal "
    "cubre todo -> 409 sin efectos. Misma clave + mismo payload -> mismo resultado; distinta -> 409.",
)
async def checkout(
    datos: CheckoutCrearDTO,
    canal: str = Query("WEB", description="Debe coincidir con datos.canal"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
    clave_idempotencia: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> CheckoutRespuestaDTO:
    clave = validar_clave_idempotencia(clave_idempotencia)
    dto, _ = await CarritoService(db).checkout(usuario, datos, _canal(canal), clave)
    return dto
