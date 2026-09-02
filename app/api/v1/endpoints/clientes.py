from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.schemas.auth import RegistroClienteDTO, ClientePerfilDTO
from backend.app.services.cliente_service import ClienteService

router = APIRouter()

@router.post(
    "",
    response_model=ClientePerfilDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo cliente (CU01 / RF01)",
    description="Crea una nueva cuenta de cliente con rol CLIENTE y estado ACTIVO tras validar que el correo no esté duplicado."
)
async def registrarCliente(
    datos_registro: RegistroClienteDTO,
    db: AsyncSession = Depends(get_db)
) -> ClientePerfilDTO:
    servicio = ClienteService(db)
    return await servicio.registrar(datos_registro)
