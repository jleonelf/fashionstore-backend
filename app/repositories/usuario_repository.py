import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.seguridad import Usuario

class UsuarioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscarPorCorreo(self, correo_electronico: str) -> Optional[Usuario]:
        query = (
            select(Usuario)
            .options(selectinload(Usuario.rol), selectinload(Usuario.cliente))
            .where(Usuario.correo_electronico == correo_electronico.strip().lower())
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def buscarPorId(self, usuario_id: uuid.UUID) -> Optional[Usuario]:
        query = (
            select(Usuario)
            .options(selectinload(Usuario.rol), selectinload(Usuario.cliente))
            .where(Usuario.id == usuario_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def crear(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        await self.db.flush()
        return usuario
