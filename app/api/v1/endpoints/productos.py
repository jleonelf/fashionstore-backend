import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.schemas.catalogo_maestros import ProductoCrearDTO, ProductoDTO, ProductoActualizarDTO
from backend.app.services.producto_service import ProductoService

router = APIRouter()

@router.post(
    "",
    response_model=ProductoDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto con imágenes y asociaciones (CU05 / RF04, RF05, RF23)",
    description="Presentación gestionarProductos() -> Controller ProductoService.crear() -> Datos ProductoRepository.crear(). Valida categoria_id, proveedor_principal_id, precio_base >=0, imagenes y temporadas/colecciones"
)
async def gestionarProductos(
    datos: ProductoCrearDTO,
    db: AsyncSession = Depends(get_db)
) -> ProductoDTO:
    servicio = ProductoService(db)
    return await servicio.crear(datos)

@router.get(
    "",
    response_model=List[ProductoDTO],
    status_code=status.HTTP_200_OK,
    summary="Listar productos (CU05, base CU06)",
    description="Controller ProductoService.listar() / CatalogoService.listar() -> Datos ProductoRepository.buscarConFiltros()"
)
async def listarProductos(
    solo_activos: bool = Query(False, description="Filtrar solo activos"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    categoria_id: Optional[uuid.UUID] = Query(None),
    marca: Optional[str] = Query(None),
    genero: Optional[str] = Query(None),
    texto: Optional[str] = Query(None, description="Búsqueda por nombre/descripción"),
    db: AsyncSession = Depends(get_db)
) -> List[ProductoDTO]:
    servicio = ProductoService(db)
    if categoria_id or marca or genero or texto:
        return await servicio.buscarConFiltros(
            texto=texto,
            categoria_id=categoria_id,
            marca=marca,
            genero=genero,
            solo_activos=solo_activos,
            limit=limit,
            offset=offset
        )
    return await servicio.listar(solo_activos=solo_activos, limit=limit, offset=offset)

@router.get(
    "/{producto_id}",
    response_model=ProductoDTO,
    status_code=status.HTTP_200_OK,
    summary="Obtener producto por ID (CU05)"
)
async def obtenerProducto(
    producto_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ProductoDTO:
    servicio = ProductoService(db)
    return await servicio.obtenerPorId(producto_id)

@router.put(
    "/{producto_id}",
    response_model=ProductoDTO,
    status_code=status.HTTP_200_OK,
    summary="Actualizar producto (CU05 / RF04)",
    description="Controller ProductoService.actualizar() -> Datos ProductoRepository.actualizar()"
)
async def actualizarProducto(
    producto_id: uuid.UUID,
    datos: ProductoActualizarDTO,
    db: AsyncSession = Depends(get_db)
) -> ProductoDTO:
    servicio = ProductoService(db)
    return await servicio.actualizar(producto_id, datos)

@router.patch(
    "/{producto_id}/activacion",
    response_model=ProductoDTO,
    status_code=status.HTTP_200_OK,
    summary="Activar/desactivar producto (CU05)"
)
async def toggleProducto(
    producto_id: uuid.UUID,
    activo: bool = Query(..., description="Nuevo estado activo"),
    db: AsyncSession = Depends(get_db)
) -> ProductoDTO:
    servicio = ProductoService(db)
    return await servicio.actualizar(producto_id, ProductoActualizarDTO(activo=activo))
