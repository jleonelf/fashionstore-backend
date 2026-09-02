from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.schemas.auth import LoginDTO, TokenRespuestaDTO, ClientePerfilDTO
from backend.app.repositories.usuario_repository import UsuarioRepository
from backend.app.core.seguridad import verificar_contrasenia, crear_token_acceso

class AutenticacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.usuario_repo = UsuarioRepository(db)

    async def iniciarSesion(self, credenciales: LoginDTO) -> TokenRespuestaDTO:
        # 1. Buscar usuario por correo
        usuario = await self.usuario_repo.buscarPorCorreo(credenciales.correo_electronico)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales de acceso incorrectas",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 2. Verificar estado de cuenta
        if usuario.estado != "ACTIVO":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta se encuentra inactiva o deshabilitada"
            )

        # 3. Validar contraseña
        if not verificar_contrasenia(credenciales.contrasenia, usuario.contrasenia_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales de acceso incorrectas",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 4. Generar Token JWT
        rol_nombre = usuario.rol.nombre if usuario.rol else "CLIENTE"
        token = crear_token_acceso(sujeto=usuario.id, rol=rol_nombre)

        perfil = ClientePerfilDTO(
            id=usuario.cliente.usuario_id if usuario.cliente else usuario.id,
            usuario_id=usuario.id,
            nombres=usuario.nombres,
            apellidos=usuario.apellidos,
            nombre_completo=usuario.nombre_completo,
            correo_electronico=usuario.correo_electronico,
            telefono=usuario.telefono,
            rol=rol_nombre,
            estado=usuario.estado,
            direccion_referencia=usuario.cliente.direccion_referencia if usuario.cliente else None,
            fecha_nacimiento=usuario.cliente.fecha_nacimiento if usuario.cliente else None,
            preferencias=usuario.cliente.preferencias if usuario.cliente else {},
            creado_en=usuario.creado_en
        )

        return TokenRespuestaDTO(
            access_token=token,
            token_type="bearer",
            usuario=perfil
        )
