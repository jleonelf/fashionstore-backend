"""Controller EntregaService — CU16 (extensión: delivery por anillos).

Cotización sin persistencia: tarifa_base + abs(anillo_destino - anillo_sucursal)
* incremento; valida rango y delivery_activo. Al confirmar (checkout) el pedido
congela sucursal, anillos, parámetros, dirección y costo. Recojo:
SOLICITADO->PREPARADO->LISTO_RECOJO->RECOGIDO. Delivery:
SOLICITADO->PREPARADO->EN_REPARTO->ENTREGADO. Cola paginada con RBAC por
sucursal. Cancelación solo si pago/inventario lo permiten (PENDIENTE_PAGO en
SOLICITADO; pagadas usan devolución CU12). Sin empresa de delivery real.
"""
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.permisos import es_admin, exigir_sucursal, rol_de
from backend.app.models.seguridad import Usuario
from backend.app.repositories.ciclo3_repository import PedidoRepository
from backend.app.repositories.sucursal_repository import SucursalRepository
from backend.app.repositories.venta_repository import VentaRepository
from backend.app.schemas.pago_stripe import CotizacionDTO, PedidoDTO

RECOJO_FLUJO = ["SOLICITADO", "PREPARADO", "LISTO_RECOJO", "RECOGIDO"]
DELIVERY_FLUJO = ["SOLICITADO", "PREPARADO", "EN_REPARTO", "ENTREGADO"]


def costo_delivery(tarifa_base, incremento, anillo_sucursal: int, anillo_destino: int) -> Decimal:
    base = Decimal(str(tarifa_base or 0))
    incr = Decimal(str(incremento or 0))
    return (base + abs(anillo_destino - anillo_sucursal) * incr).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


class EntregaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pedido_repo = PedidoRepository(db)
        self.sucursal_repo = SucursalRepository(db)
        self.venta_repo = VentaRepository(db)

    async def cotizar(self, sucursal_id: uuid.UUID, anillo_destino: int) -> CotizacionDTO:
        sucursal = await self.sucursal_repo.buscarPorId(sucursal_id)
        if sucursal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
        if not sucursal.delivery_activo:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sucursal sin delivery activo")
        minimo = int(sucursal.anillo_minimo_delivery or 1)
        maximo = int(sucursal.anillo_maximo_delivery or 10)
        if not (minimo <= anillo_destino <= maximo):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Anillo fuera de rango [{minimo}, {maximo}]",
            )
        anillo_suc = int(sucursal.numero_anillo or minimo)
        base = Decimal(str(sucursal.tarifa_base_delivery or 0))
        incr = Decimal(str(sucursal.incremento_anillo_delivery or 0))
        return CotizacionDTO(
            sucursal_id=sucursal.id, anillo_sucursal=anillo_suc,
            anillo_destino=anillo_destino, tarifa_base=base,
            incremento_anillo=incr,
            costo_entrega=costo_delivery(base, incr, anillo_suc, anillo_destino),
        )

    def _a_dto(self, pedido) -> PedidoDTO:
        return PedidoDTO.model_validate(pedido)

    def _autorizar_cola(self, usuario: Usuario, sucursal_id: Optional[uuid.UUID]) -> None:
        if es_admin(usuario):
            return
        rol = rol_de(usuario)
        if rol in ("ENCARGADO", "CAJERO"):
            if sucursal_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Indique la sucursal de su ámbito",
                )
            exigir_sucursal(usuario, sucursal_id)
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo personal operativo o Administrador")

    def _autorizar_pedido(self, usuario: Usuario, pedido) -> None:
        if es_admin(usuario):
            return
        rol = rol_de(usuario)
        if rol == "CLIENTE":
            if pedido.cliente_id != usuario.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pedido de otro cliente")
            return
        if rol in ("ENCARGADO", "CAJERO"):
            exigir_sucursal(usuario, pedido.sucursal_id)
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rol no autorizado")

    async def mis_pedidos(self, usuario: Usuario, limit=50, offset=0):
        if rol_de(usuario) != "CLIENTE":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el Cliente consulta sus pedidos")
        items, total = await self.pedido_repo.pedidosDeCliente(usuario.id, limit=limit, offset=offset)
        return {"total": total, "limit": limit, "offset": offset,
                "items": [self._a_dto(p) for p in items]}

    async def obtener(self, usuario: Usuario, pedido_id: uuid.UUID) -> PedidoDTO:
        pedido = await self.pedido_repo.buscarPorId(pedido_id)
        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
        self._autorizar_pedido(usuario, pedido)
        return self._a_dto(pedido)

    async def cola(
        self, usuario: Usuario, sucursal_id: Optional[uuid.UUID] = None,
        estado: Optional[str] = None, limit: int = 50, offset: int = 0,
    ):
        self._autorizar_cola(usuario, sucursal_id)
        items, total = await self.pedido_repo.cola(
            sucursal_id=sucursal_id, estado=estado, limit=limit, offset=offset
        )
        return {"total": total, "limit": limit, "offset": offset,
                "items": [self._a_dto(p) for p in items]}

    async def transicionar(self, usuario: Usuario, pedido_id: uuid.UUID, destino: str) -> PedidoDTO:
        pedido = await self.pedido_repo.buscarPorId(pedido_id)
        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
        rol = rol_de(usuario)
        if rol not in ("ENCARGADO", "CAJERO") and not es_admin(usuario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo personal operativo")
        if not es_admin(usuario):
            exigir_sucursal(usuario, pedido.sucursal_id)
        if destino == pedido.estado:
            return self._a_dto(pedido)  # idempotente
        flujo = RECOJO_FLUJO if pedido.modalidad == "RECOJO" else DELIVERY_FLUJO
        if destino == "CANCELADO":
            return await self.cancelar(usuario, pedido_id)
        if destino not in flujo:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transición inválida para {pedido.modalidad}: {pedido.estado} -> {destino}",
            )
        actual_idx = flujo.index(pedido.estado) if pedido.estado in flujo else -1
        if flujo.index(destino) != actual_idx + 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transición no secuencial: {pedido.estado} -> {destino}",
            )
        if pedido.estado == "SOLICITADO" and destino == "PREPARADO":
            venta = await self.venta_repo.buscarPorId(pedido.venta_id)
            estado_v = venta.estado if isinstance(venta.estado, str) else venta.estado.name
            if estado_v != "PAGADA":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Solo pedidos pagados entran a preparación",
                )
        try:
            pedido.estado = destino
            await self.db.flush()
            await self.db.commit()
            return self._a_dto(pedido)
        except Exception:
            await self.db.rollback()
            raise

    async def cancelar(self, usuario: Usuario, pedido_id: uuid.UUID) -> PedidoDTO:
        pedido = await self.pedido_repo.buscarPorId(pedido_id)
        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
        rol = rol_de(usuario)
        if rol == "CLIENTE" and pedido.cliente_id != usuario.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pedido de otro cliente")
        if rol in ("ENCARGADO", "CAJERO") and not es_admin(usuario):
            exigir_sucursal(usuario, pedido.sucursal_id)
        if pedido.estado in ("RECOGIDO", "ENTREGADO", "CANCELADO"):
            if pedido.estado == "CANCELADO":
                return self._a_dto(pedido)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pedido ya finalizado")
        venta = await self.venta_repo.buscarPorId(pedido.venta_id)
        estado_v = venta.estado if isinstance(venta.estado, str) else venta.estado.name
        if estado_v == "PAGADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pedido pagado: la cancelación usa devolución (CU12), no cancela stock digital",
            )
        if estado_v != "PENDIENTE_PAGO" or pedido.estado != "SOLICITADO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se cancela en SOLICITADO con venta PENDIENTE_PAGO",
            )
        # Cancelación permitida: marca la venta como vencida y reutiliza la
        # expiración (liberación del compromiso exactamente una vez).
        from backend.app.services.stripe_service import StripeService

        try:
            venta.expira_en = venta.creada_en  # fuerza condición de vencida
            await self.db.flush()
            await self.db.commit()
            resumen = await StripeService(self.db).cancelarVencidas(lote=1000)
            pedido = await self.pedido_repo.buscarPorId(pedido_id)
            if pedido.estado != "CANCELADO":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se pudo cancelar el pedido",
                )
            return self._a_dto(pedido)
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise
