"""Presentación Entregas — CU16 (recojo/delivery por anillos)."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.dependencias import get_usuario_actual
from backend.app.models.seguridad import Usuario
from backend.app.schemas.pago_stripe import CotizacionDTO, PedidoDTO, PedidoListaDTO, TransicionPedidoDTO
from backend.app.services.entrega_service import EntregaService

router = APIRouter()


@router.get(
    "/cotizacion", response_model=CotizacionDTO,
    summary="Cotizar delivery sin persistencia (CU16)",
    description="Fórmula: tarifa_base + abs(anillo_destino - anillo_sucursal) * incremento. "
    "Valida rango de anillos y delivery activo.",
)
async def cotizar(
    sucursal_id: uuid.UUID,
    anillo_destino: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> CotizacionDTO:
    return await EntregaService(db).cotizar(sucursal_id, anillo_destino)


@router.get(
    "/mis-pedidos", response_model=PedidoListaDTO, summary="Mis pedidos de entrega (CU16)",
)
async def misPedidos(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    return await EntregaService(db).mis_pedidos(usuario, limit=limit, offset=offset)


@router.get(
    "/cola", response_model=PedidoListaDTO, summary="Cola operativa por sucursal (CU16)",
    description="Paginada y filtrada por sucursal. RBAC: ADMIN global; ENCARGADO/CAJERO su sucursal.",
)
async def colaOperativa(
    sucursal_id: Optional[uuid.UUID] = Query(None),
    estado: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    return await EntregaService(db).cola(usuario, sucursal_id=sucursal_id, estado=estado, limit=limit, offset=offset)


@router.get(
    "/{pedido_id}", response_model=PedidoDTO, summary="Consultar pedido (CU16)",
)
async def obtenerPedido(
    pedido_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> PedidoDTO:
    return await EntregaService(db).obtener(usuario, pedido_id)


@router.patch(
    "/{pedido_id}/estado", response_model=PedidoDTO, summary="Avanzar estado del pedido (CU16)",
    description="Recojo: SOLICITADO→PREPARADO→LISTO_RECOJO→RECOGIDO. "
    "Delivery: SOLICITADO→PREPARADO→EN_REPARTO→ENTREGADO. Secuencial; repetición idempotente. "
    "Solo pedidos pagados entran a preparación.",
)
async def transicionarPedido(
    pedido_id: uuid.UUID,
    datos: TransicionPedidoDTO,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> PedidoDTO:
    return await EntregaService(db).transicionar(usuario, pedido_id, datos.estado)


@router.post(
    "/{pedido_id}/cancelar", response_model=PedidoDTO, summary="Cancelar pedido (CU16)",
    description="Solo en SOLICITADO con venta PENDIENTE_PAGO (libera el compromiso una vez). "
    "Pedidos pagados usan devolución (CU12).",
)
async def cancelarPedido(
    pedido_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> PedidoDTO:
    return await EntregaService(db).cancelar(usuario, pedido_id)
