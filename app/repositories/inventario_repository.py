import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.inventario import InventarioSucursal
from backend.app.models.organizacion import Sucursal, Ciudad

class InventarioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def existenciaTotalPorVariante(self, variante_id: uuid.UUID) -> int:
        """Suma global disponible+reservado+comprometido+en_transito para variante."""
        query = select(
            func.coalesce(
                func.sum(
                    InventarioSucursal.disponible
                    + InventarioSucursal.reservado
                    + InventarioSucursal.comprometido_traslado
                    + InventarioSucursal.en_transito
                ),
                0,
            )
        ).where(InventarioSucursal.variante_id == variante_id)
        result = await self.db.execute(query)
        return int(result.scalar() or 0)

    async def buscarPorVarianteYSucursal(self, variante_id: uuid.UUID, sucursal_id: uuid.UUID) -> Optional[InventarioSucursal]:
        query = select(InventarioSucursal).where(
            InventarioSucursal.variante_id == variante_id,
            InventarioSucursal.sucursal_id == sucursal_id,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def ingresar(self, variante_id: uuid.UUID, sucursal_id: uuid.UUID, cantidad: int) -> InventarioSucursal:
        """Upsert inventario: incrementa disponible. Crea registro si no existe."""
        registro = await self.buscarPorVarianteYSucursal(variante_id, sucursal_id)
        if registro is None:
            registro = InventarioSucursal(
                variante_id=variante_id,
                sucursal_id=sucursal_id,
                disponible=cantidad,
                reservado=0,
                comprometido_traslado=0,
                en_transito=0,
            )
            self.db.add(registro)
            await self.db.flush()
        else:
            registro.disponible = registro.disponible + cantidad
            await self.db.flush()
        return registro

    async def porVariante(self, variante_id: uuid.UUID) -> List[InventarioSucursal]:
        """
        CU06 - porVariante: SELECT inventario_sucursal WHERE variante_id AND disponible > 0
        Solo lectura, no modifica inventario. Filtra disponible>0.
        Performance: JOIN productos-variantes-inventario está en capas superiores; aquí directo.
        """
        query = select(InventarioSucursal).where(
            InventarioSucursal.variante_id == variante_id,
            InventarioSucursal.disponible > 0
        ).order_by(InventarioSucursal.sucursal_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def porVarianteEnriquecido(self, variante_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        CU06 - porVariante con JOIN sucursales/ciudades WHERE disponible>0
        Retorna Sucursal + cantidades separadas (disponible, reservado, comprometido_traslado, en_transito)
        No total global, por sucursal. Diferenciando campos.
        """
        # Join inventario -> sucursal -> ciudad
        query = (
            select(InventarioSucursal, Sucursal, Ciudad)
            .join(Sucursal, Sucursal.id == InventarioSucursal.sucursal_id)
            .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
            .where(
                InventarioSucursal.variante_id == variante_id,
                InventarioSucursal.disponible > 0
            )
            .order_by(Sucursal.nombre)
        )
        result = await self.db.execute(query)
        rows = result.all()
        enriched = []
        for inv, suc, ciu in rows:
            enriched.append({
                "inventario_id": inv.id,
                "variante_id": inv.variante_id,
                "sucursal_id": suc.id,
                "sucursal_nombre": suc.nombre,
                "ciudad_id": ciu.id,
                "ciudad_nombre": ciu.nombre,
                "direccion": suc.direccion,
                "telefono": suc.telefono,
                "disponible": inv.disponible,
                "reservado": inv.reservado,
                "comprometido_traslado": inv.comprometido_traslado,
                "en_transito": inv.en_transito,
                "actualizado_en": inv.actualizado_en,
            })
        return enriched

    async def disponibilidadPorSucursal(self, variante_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Alias de porVarianteEnriquecido para contrato InventarioService.disponibilidadPorSucursal()
        """
        return await self.porVarianteEnriquecido(variante_id)

    async def existencias(self, sucursal_id: Optional[uuid.UUID] = None) -> List[InventarioSucursal]:
        query = select(InventarioSucursal)
        if sucursal_id:
            query = query.where(InventarioSucursal.sucursal_id == sucursal_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
