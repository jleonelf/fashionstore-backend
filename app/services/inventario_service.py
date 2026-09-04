import uuid
from typing import List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.repositories.inventario_repository import InventarioRepository
from backend.app.repositories.variante_repository import VarianteRepository

class InventarioService:
    """
    Controller InventarioService.disponibilidadPorSucursal() para CU06 (RF08)
    Presentación consultarDisponibilidad() -> Controller InventarioService.disponibilidadPorSucursal() -> Datos InventarioRepository.porVariante()
    Solo lectura, no modifica inventario.
    Diferencia disponible, reservado, comprometido_traslado, en_transito. Por sucursal, no total global.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventario_repo = InventarioRepository(db)
        self.variante_repo = VarianteRepository(db)

    async def disponibilidadPorSucursal(self, variante_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Retorna lista por sucursal con cantidad disponible >0, diferenciada.
        Performance: SELECT inventario_sucursal JOIN sucursales/ciudades WHERE disponible>0
        """
        # Validar variante existe
        variante = await self.variante_repo.buscarPorId(variante_id)
        if not variante:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada")

        # Usar repo enriquecido que hace JOIN y filtra disponible>0
        disponibilidad = await self.inventario_repo.disponibilidadPorSucursal(variante_id)
        # No suma global, ya es por sucursal
        return disponibilidad

    async def consultarDisponibilidad(self, variante_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Alias para compatibilidad"""
        return await self.disponibilidadPorSucursal(variante_id)

    async def porVariante(self, variante_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Alias datos InventarioRepository.porVariante()"""
        return await self.disponibilidadPorSucursal(variante_id)
