import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.schemas.catalogo_maestros import VarianteCrearDTO, VarianteDTO, VarianteActualizarDTO
from backend.app.services.variante_service import VarianteService

router = APIRouter()

@router.post(
    "",
    response_model=VarianteDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear variante de producto (CU05 / RF05)",
    description="Presentación gestionarVariantes() -> Controller VarianteService.crear() -> Datos VarianteRepository.crear(). UQ producto+talla+color, sku único, codigo_barras único, precio >=0, activa. 409 Conflict si duplica."
)
async def gestionarVariantes(
    datos: VarianteCrearDTO,
    db: AsyncSession = Depends(get_db)
) -> VarianteDTO:
    servicio = VarianteService(db)
    return await servicio.crear(datos)

@router.get(
    "",
    response_model=List[VarianteDTO],
    status_code=status.HTTP_200_OK,
    summary="Listar variantes (CU05)",
    description="VarianteRepository.listar() — base para CU06 disponibilidad"
)
async def listarVariantes(
    producto_id: Optional[uuid.UUID] = Query(None, description="Filtrar por producto"),
    solo_activas: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
) -> List[VarianteDTO]:
    servicio = VarianteService(db)
    return await servicio.listar(producto_id=producto_id, solo_activas=solo_activas, limit=limit, offset=offset)

@router.get(
    "/{variante_id}",
    response_model=VarianteDTO,
    status_code=status.HTTP_200_OK,
    summary="Obtener variante por ID (CU05)"
)
async def obtenerVariante(
    variante_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> VarianteDTO:
    servicio = VarianteService(db)
    return await servicio.obtenerPorId(variante_id)

@router.put(
    "/{variante_id}",
    response_model=VarianteDTO,
    status_code=status.HTTP_200_OK,
    summary="Actualizar variante (CU05)"
)
async def actualizarVariante(
    variante_id: uuid.UUID,
    datos: VarianteActualizarDTO,
    db: AsyncSession = Depends(get_db)
) -> VarianteDTO:
    servicio = VarianteService(db)
    return await servicio.actualizar(variante_id, datos)

@router.patch(
    "/{variante_id}/activacion",
    response_model=VarianteDTO,
    status_code=status.HTTP_200_OK,
    summary="Activar/desactivar variante (CU05)"
)
async def toggleVariante(
    variante_id: uuid.UUID,
    activa: bool = Query(..., description="Nuevo estado activo"),
    db: AsyncSession = Depends(get_db)
) -> VarianteDTO:
    servicio = VarianteService(db)
    return await servicio.actualizar(variante_id, VarianteActualizarDTO(activa=activa))
