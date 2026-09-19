"""Datos Ciclo 3 — promociones, carrito, entregas, IA (CU22/CU14/CU16-21/25).

Solo flush; el servicio confirma o revierte en una única transacción.
"""
import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ciclo3 import (
    Carrito, DetalleCarrito, HistorialNavegacion, PedidoEntrega,
    Promocion, PromocionVariante, SolicitudIA,
)


class PromocionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear(self, promo: Promocion) -> Promocion:
        self.db.add(promo)
        await self.db.flush()
        return promo

    async def buscarPorId(self, promo_id: uuid.UUID) -> Optional[Promocion]:
        return await self.db.get(Promocion, promo_id)

    async def buscarPorCodigo(self, codigo: str) -> Optional[Promocion]:
        r = await self.db.execute(select(Promocion).where(Promocion.codigo == codigo))
        return r.scalars().first()

    async def listar(self, solo_activas: bool = False, limit: int = 50, offset: int = 0):
        base = select(Promocion).order_by(Promocion.creada_en.desc())
        conteo = select(func.count()).select_from(Promocion)
        if solo_activas:
            base = base.where(Promocion.activa.is_(True))
            conteo = conteo.where(Promocion.activa.is_(True))
        total = int((await self.db.execute(conteo)).scalar() or 0)
        items = list((await self.db.execute(base.limit(limit).offset(offset))).scalars().all())
        return items, total

    async def variantesDe(self, promo_id: uuid.UUID) -> List[uuid.UUID]:
        r = await self.db.execute(
            select(PromocionVariante.variante_id).where(PromocionVariante.promocion_id == promo_id)
        )
        return list(r.scalars().all())

    async def asociar(self, promo_id: uuid.UUID, variante_id: uuid.UUID) -> None:
        self.db.add(PromocionVariante(promocion_id=promo_id, variante_id=variante_id))
        await self.db.flush()

    async def desasociar(self, promo_id: uuid.UUID, variante_id: uuid.UUID) -> bool:
        r = await self.db.execute(
            select(PromocionVariante).where(
                PromocionVariante.promocion_id == promo_id,
                PromocionVariante.variante_id == variante_id,
            )
        )
        fila = r.scalars().first()
        if fila is None:
            return False
        await self.db.delete(fila)
        await self.db.flush()
        return True

    async def vigentesPorVariante(self, variante_id: uuid.UUID, ahora: datetime) -> List[Promocion]:
        """Promociones activas y vigentes asociadas a la variante."""
        q = (
            select(Promocion)
            .join(PromocionVariante, PromocionVariante.promocion_id == Promocion.id)
            .where(PromocionVariante.variante_id == variante_id)
            .where(Promocion.activa.is_(True))
            .where((Promocion.vigencia_inicio.is_(None)) | (Promocion.vigencia_inicio <= ahora))
            .where((Promocion.vigencia_fin.is_(None)) | (Promocion.vigencia_fin >= ahora))
            .order_by(Promocion.id)
        )
        return list((await self.db.execute(q)).scalars().all())


class CarritoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def activoDe(self, cliente_id: uuid.UUID, canal: str) -> Optional[Carrito]:
        r = await self.db.execute(
            select(Carrito).where(
                Carrito.cliente_id == cliente_id, Carrito.canal == canal,
                Carrito.estado == "ACTIVO",
            )
        )
        return r.scalars().first()

    async def buscarPorId(self, carrito_id: uuid.UUID) -> Optional[Carrito]:
        return await self.db.get(Carrito, carrito_id)

    async def crear(self, carrito: Carrito) -> Carrito:
        self.db.add(carrito)
        await self.db.flush()
        return carrito

    async def lineasDe(self, carrito_id: uuid.UUID) -> List[DetalleCarrito]:
        r = await self.db.execute(
            select(DetalleCarrito).where(DetalleCarrito.carrito_id == carrito_id)
        )
        return list(r.scalars().all())

    async def lineaPorVariante(self, carrito_id: uuid.UUID, variante_id: uuid.UUID) -> Optional[DetalleCarrito]:
        r = await self.db.execute(
            select(DetalleCarrito).where(
                DetalleCarrito.carrito_id == carrito_id,
                DetalleCarrito.variante_id == variante_id,
            )
        )
        return r.scalars().first()

    async def agregarLinea(self, linea: DetalleCarrito) -> DetalleCarrito:
        self.db.add(linea)
        await self.db.flush()
        return linea

    async def eliminarLinea(self, linea: DetalleCarrito) -> None:
        await self.db.delete(linea)
        await self.db.flush()


class PedidoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear(self, pedido: PedidoEntrega) -> PedidoEntrega:
        self.db.add(pedido)
        await self.db.flush()
        return pedido

    async def buscarPorId(self, pedido_id: uuid.UUID) -> Optional[PedidoEntrega]:
        return await self.db.get(PedidoEntrega, pedido_id)

    async def buscarPorVenta(self, venta_id: uuid.UUID) -> Optional[PedidoEntrega]:
        r = await self.db.execute(select(PedidoEntrega).where(PedidoEntrega.venta_id == venta_id))
        return r.scalars().first()

    async def cola(
        self, sucursal_id: Optional[uuid.UUID] = None, estado: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> Tuple[List[PedidoEntrega], int]:
        base = select(PedidoEntrega).order_by(PedidoEntrega.creada_en.desc())
        conteo = select(func.count()).select_from(PedidoEntrega)
        if sucursal_id is not None:
            base = base.where(PedidoEntrega.sucursal_id == sucursal_id)
            conteo = conteo.where(PedidoEntrega.sucursal_id == sucursal_id)
        if estado is not None:
            base = base.where(PedidoEntrega.estado == estado)
            conteo = conteo.where(PedidoEntrega.estado == estado)
        total = int((await self.db.execute(conteo)).scalar() or 0)
        items = list((await self.db.execute(base.limit(limit).offset(offset))).scalars().all())
        return items, total

    async def pedidosDeCliente(
        self, cliente_id: uuid.UUID, limit: int = 50, offset: int = 0,
    ) -> Tuple[List[PedidoEntrega], int]:
        base = (
            select(PedidoEntrega).where(PedidoEntrega.cliente_id == cliente_id)
            .order_by(PedidoEntrega.creada_en.desc())
        )
        conteo = select(func.count()).select_from(PedidoEntrega).where(
            PedidoEntrega.cliente_id == cliente_id
        )
        total = int((await self.db.execute(conteo)).scalar() or 0)
        items = list((await self.db.execute(base.limit(limit).offset(offset))).scalars().all())
        return items, total


class NavegacionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def registrar(self, evento: HistorialNavegacion) -> HistorialNavegacion:
        self.db.add(evento)
        await self.db.flush()
        return evento

    async def historialCliente(self, cliente_id: uuid.UUID, limit: int = 100) -> List[HistorialNavegacion]:
        r = await self.db.execute(
            select(HistorialNavegacion)
            .where(HistorialNavegacion.cliente_id == cliente_id)
            .order_by(HistorialNavegacion.creada_en.desc())
            .limit(limit)
        )
        return list(r.scalars().all())


class SolicitudIaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear(self, solicitud: SolicitudIA) -> SolicitudIA:
        self.db.add(solicitud)
        await self.db.flush()
        return solicitud
