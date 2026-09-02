import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.seguridad import Usuario
from backend.app.schemas.usuario import UsuarioCrearDTO, UsuarioListadoDTO
from backend.app.repositories.usuario_repository import UsuarioRepository
from backend.app.repositories.rol_repository import RolRepository
from backend.app.core.seguridad import generar_contrasenia_hash

class UsuarioService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.usuario_repo = UsuarioRepository(db)
        self.rol_repo = RolRepository(db)

    async def crear(self, dto: UsuarioCrearDTO) -> UsuarioListadoDTO:
        # 1. Validar correo no duplicado
        existente = await self.usuario_repo.buscarPorCorreo(dto.correo_electronico)
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya se encuentra registrado para otro usuario"
            )

        # 2. Validar que el rol exista
        rol = await self.rol_repo.buscarPorId(dto.rol_id)
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El rol especificado no existe en el sistema"
            )

        # 3. Hashear contraseña y crear usuario
        contrasenia_hash = generar_contrasenia_hash(dto.contrasenia)
        nuevo_usuario = Usuario(
            rol_id=dto.rol_id,
            nombres=dto.nombres.strip(),
            apellidos=dto.apellidos.strip(),
            correo_electronico=dto.correo_electronico.strip().lower(),
            contrasenia_hash=contrasenia_hash,
            telefono=dto.telefono.strip() if dto.telefono else None,
            estado="ACTIVO"
        )
        await self.usuario_repo.crear(nuevo_usuario)
        await self.db.commit()
        await self.db.refresh(nuevo_usuario)

        return UsuarioListadoDTO(
            id=nuevo_usuario.id,
            rol_id=nuevo_usuario.rol_id,
            rol_nombre=rol.nombre,
            nombres=nuevo_usuario.nombres,
            apellidos=nuevo_usuario.apellidos,
            nombre_completo=nuevo_usuario.nombre_completo,
            correo_electronico=nuevo_usuario.correo_electronico,
            telefono=nuevo_usuario.telefono,
            estado=nuevo_usuario.estado,
            creado_en=nuevo_usuario.creado_en,
            actualizado_en=nuevo_usuario.actualizado_en
        )

    async def listar(self, rol_id: Optional[uuid.UUID] = None, estado: Optional[str] = None) -> List[UsuarioListadoDTO]:
        usuarios = await self.usuario_repo.listar(rol_id=rol_id, estado=estado)
        return [
            UsuarioListadoDTO(
                id=u.id,
                rol_id=u.rol_id,
                rol_nombre=u.rol.nombre if u.rol else "SIN ROL",
                nombres=u.nombres,
                apellidos=u.apellidos,
                nombre_completo=u.nombre_completo,
                correo_electronico=u.correo_electronico,
                telefono=u.telefono,
                estado=u.estado,
                creado_en=u.creado_en,
                actualizado_en=u.actualizado_en
            )
            for u in usuarios
        ]

    async def asignarRol(self, usuario_id: uuid.UUID, nuevo_rol_id: uuid.UUID) -> UsuarioListadoDTO:
        usuario = await self.usuario_repo.buscarPorId(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        rol = await self.rol_repo.buscarPorId(nuevo_rol_id)
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El rol especificado no existe"
            )

        usuario_actualizado = await self.usuario_repo.asignarRol(usuario_id, nuevo_rol_id)
        await self.db.commit()

        return UsuarioListadoDTO(
            id=usuario_actualizado.id,
            rol_id=usuario_actualizado.rol_id,
            rol_nombre=rol.nombre,
            nombres=usuario_actualizado.nombres,
            apellidos=usuario_actualizado.apellidos,
            nombre_completo=usuario_actualizado.nombre_completo,
            correo_electronico=usuario_actualizado.correo_electronico,
            telefono=usuario_actualizado.telefono,
            estado=usuario_actualizado.estado,
            creado_en=usuario_actualizado.creado_en,
            actualizado_en=usuario_actualizado.actualizado_en
        )

    async def actualizarEstado(self, usuario_id: uuid.UUID, nuevo_estado: str) -> UsuarioListadoDTO:
        usuario = await self.usuario_repo.buscarPorId(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        usuario_actualizado = await self.usuario_repo.actualizarEstado(usuario_id, nuevo_estado)
        await self.db.commit()

        return UsuarioListadoDTO(
            id=usuario_actualizado.id,
            rol_id=usuario_actualizado.rol_id,
            rol_nombre=usuario_actualizado.rol.nombre if usuario_actualizado.rol else "SIN ROL",
            nombres=usuario_actualizado.nombres,
            apellidos=usuario_actualizado.apellidos,
            nombre_completo=usuario_actualizado.nombre_completo,
            correo_electronico=usuario_actualizado.correo_electronico,
            telefono=usuario_actualizado.telefono,
            estado=usuario_actualizado.estado,
            creado_en=usuario_actualizado.creado_en,
            actualizado_en=usuario_actualizado.actualizado_en
        )

    async def desactivar(self, usuario_id: uuid.UUID) -> UsuarioListadoDTO:
        return await self.actualizarEstado(usuario_id, "INACTIVO")
