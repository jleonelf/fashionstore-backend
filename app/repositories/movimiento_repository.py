import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.inventario import MovimientoInventario

class MovimientoRepository:
    """
    Datos MovimientoRepository.listar() para CU07 (RF22)
    Kardex inmutable: cada cambio genera movimiento con tipo, cantidad, costo_unitario, responsable, referencia.
    Solo lectura + exposición de movimientos ya creados por CU04.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def registrar(self, movimiento: MovimientoInventario) -> MovimientoInventario:
        """Persistir movimiento Kardex. Tipo esperado RECEPCION_PROVEEDOR para CU04/Ciclo1."""
        self.db.add(movimiento)
        await self.db.flush()
        return movimiento

    async def listar(
        self,
        variante_id: Optional[uuid.UUID] = None,
        sucursal_id: Optional[uuid.UUID] = None,
        tipo: Optional[str] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MovimientoInventario]:
        """
        CU07 - listar(variante_id, sucursal_id, tipo, desde, hasta, limit)
        Filtros opcionales, orden fecha_hora desc (Kardex auditoría). 
        Tipos Ciclo1 al menos RECEPCION_PROVEEDOR.
        """
        query = select(MovimientoInventario).order_by(MovimientoInventario.fecha_hora.desc())
        if variante_id:
            query = query.where(MovimientoInventario.variante_id == variante_id)
        if sucursal_id:
            query = query.where(
                (MovimientoInventario.sucursal_origen_id == sucursal_id)
                | (MovimientoInventario.sucursal_destino_id == sucursal_id)
            )
        if tipo:
            query = query.where(MovimientoInventario.tipo == tipo)
        if desde:
            query = query.where(MovimientoInventario.fecha_hora >= desde)
        if hasta:
            query = query.where(MovimientoInventario.fecha_hora <= hasta)
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def listarPaginado(
        self,
        variante_id: Optional[uuid.UUID] = None,
        sucursal_id: Optional[uuid.UUID] = None,
        tipo: Optional[str] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Paginado con total count para presentación consultarKardex()"""
        # Count
        count_q = select(func.count()).select_from(MovimientoInventario)
        if variante_id:
            count_q = count_q.where(MovimientoInventario.variante_id == variante_id)
        if sucursal_id:
            count_q = count_q.where(
                (MovimientoInventario.sucursal_origen_id == sucursal_id)
                | (MovimientoInventario.sucursal_destino_id == sucursal_id)
            )
        if tipo:
            count_q = count_q.where(MovimientoInventario.tipo == tipo)
        if desde:
            count_q = count_q.where(MovimientoInventario.fecha_hora >= desde)
        if hasta:
            count_q = count_q.where(MovimientoInventario.fecha_hora <= hasta)
        total_res = await self.db.execute(count_q)
        total = int(total_res.scalar() or 0)

        items = await self.listar(
            variante_id=variante_id,
            sucursal_id=sucursal_id,
            tipo=tipo,
            desde=desde,
            hasta=hasta,
            limit=limit,
            offset=offset,
        )
        return {"total": total, "items": items, "limit": limit, "offset": offset}

    async def buscarPorId(self, movimiento_id: uuid.UUID) -> Optional[MovimientoInventario]:
        query = select(MovimientoInventario).where(MovimientoInventario.id == movimiento_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def listarPorReferencia(self, referencia_tipo: str, referencia_id: uuid.UUID) -> List[MovimientoInventario]:
        query = select(MovimientoInventario).where(
            MovimientoInventario.referencia_tipo == referencia_tipo,
            MovimientoInventario.referencia_id == referencia_id,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
