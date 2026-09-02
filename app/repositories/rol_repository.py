from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.seguridad import Rol

class RolRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscarPorNombre(self, nombre: str) -> Optional[Rol]:
        query = select(Rol).where(Rol.nombre == nombre)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def crear(self, nombre: str, descripcion: Optional[str] = None) -> Rol:
        rol = Rol(nombre=nombre, descripcion=descripcion, activo=True)
        self.db.add(rol)
        await self.db.flush()
        return rol
