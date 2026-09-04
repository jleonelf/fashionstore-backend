import uuid
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.repositories.producto_repository import ProductoRepository
from backend.app.schemas.catalogo_maestros import ProductoDTO

class CatalogoService:
    """
    Controller CatalogoService.listar()/filtrar() para CU06
    Presentación consultarCatalogo(), filtrarCatalogo() -> Controller CatalogoService.* -> Datos ProductoRepository.buscarConFiltros()
    Solo lectura, filtra activos, paginación, búsqueda por texto y filtros avanzados en tiempo real.
    Performance: JOIN productos-variantes-inventario (aquí variantes + producto_temporada/coleccion)
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.producto_repo = ProductoRepository(db)

    async def listar(self, solo_activos: bool = True, limit: int = 50, offset: int = 0, **filtros_extra) -> List[ProductoDTO]:
        """
        CatalogoService.listar(): mostrar prendas activas, sin filtros o con filtros opcionales base.
        Delegado a buscarConFiltros con activo=true.
        """
        # Si se pasan filtros_extra (categoria etc), delegar a filtrar
        if filtros_extra:
            return await self.filtrar(filtros=filtros_extra, solo_activos=solo_activos, limit=limit, offset=offset)
        productos = await self.producto_repo.listar(solo_activos=solo_activos, limit=limit, offset=offset)
        # Enriquecer igual que producto_service
        result = []
        for p in productos:
            imagenes = await self.producto_repo.listarImagenesPorProducto(p.id)
            temporada_ids = await self.producto_repo.listarTemporadaIds(p.id)
            coleccion_ids = await self.producto_repo.listarColeccionIds(p.id)
            from backend.app.schemas.catalogo_maestros import ImagenProductoDTO
            result.append(ProductoDTO(
                id=p.id,
                categoria_id=p.categoria_id,
                proveedor_principal_id=p.proveedor_principal_id,
                nombre=p.nombre,
                descripcion=p.descripcion,
                genero=p.genero,
                marca=p.marca,
                precio_base=p.precio_base,
                activo=p.activo,
                creado_en=p.creado_en,
                actualizado_en=p.actualizado_en,
                imagenes=[ImagenProductoDTO.model_validate(i) for i in imagenes],
                temporada_ids=temporada_ids,
                coleccion_ids=coleccion_ids
            ))
        return result

    async def filtrar(
        self,
        filtros: Optional[Dict[str, Any]] = None,
        texto: Optional[str] = None,
        busqueda: Optional[str] = None,
        categoria_id: Optional[uuid.UUID] = None,
        talla_id: Optional[uuid.UUID] = None,
        color_id: Optional[uuid.UUID] = None,
        temporada_id: Optional[uuid.UUID] = None,
        coleccion_id: Optional[uuid.UUID] = None,
        genero: Optional[str] = None,
        marca: Optional[str] = None,
        precio_min: Optional[float] = None,
        precio_max: Optional[float] = None,
        codigo_hex: Optional[str] = None,
        solo_activos: bool = True,
        limit: int = 50,
        offset: int = 0,
        activo: Optional[bool] = None
    ) -> List[ProductoDTO]:
        """
        CatalogoService.filtrar(): filtros avanzados en tiempo real
        categoria, talla, color, temporada, colección, precio (rango), género, marca, búsqueda texto.
        Debe mostrar todas pero con info (no filtrar por disponibilidad). Solo lectura.
        """
        # Normalizar filtros dict si se pasó
        if filtros is not None:
            # filtros puede contener keys extra
            # extraer con prioridad a parámetros explícitos
            if isinstance(filtros, dict):
                # si algún param explícito es None, tomar del dict
                if texto is None and "texto" in filtros:
                    texto = filtros.get("texto")
                if busqueda is None and "busqueda" in filtros:
                    busqueda = filtros.get("busqueda")
                if categoria_id is None and "categoria_id" in filtros:
                    categoria_id = filtros.get("categoria_id")
                if talla_id is None and "talla_id" in filtros:
                    talla_id = filtros.get("talla_id")
                if color_id is None and "color_id" in filtros:
                    color_id = filtros.get("color_id")
                if temporada_id is None and "temporada_id" in filtros:
                    temporada_id = filtros.get("temporada_id")
                if coleccion_id is None and "coleccion_id" in filtros:
                    coleccion_id = filtros.get("coleccion_id")
                if genero is None and "genero" in filtros:
                    genero = filtros.get("genero")
                if marca is None and "marca" in filtros:
                    marca = filtros.get("marca")
                if precio_min is None and "precio_min" in filtros:
                    precio_min = filtros.get("precio_min")
                if precio_max is None and "precio_max" in filtros:
                    precio_max = filtros.get("precio_max")
                if codigo_hex is None and ("codigo_hex" in filtros or "color_hex" in filtros):
                    codigo_hex = filtros.get("codigo_hex", filtros.get("color_hex"))
                if activo is not None:
                    solo_activos = activo
                elif "activo" in filtros:
                    solo_activos = filtros["activo"] not in [False, "false", "False", 0]
                    if filtros["activo"] is False or str(filtros["activo"]).lower() == "false":
                        solo_activos = False
            else:
                texto = filtros

        # Alias busqueda
        if busqueda and not texto:
            texto = busqueda

        # Validar precio rango
        if precio_min is not None and precio_max is not None:
            if float(precio_min) > float(precio_max):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="precio_min no puede ser mayor que precio_max")

        productos = await self.producto_repo.buscarConFiltros(
            texto=texto,
            categoria_id=categoria_id,
            talla_id=talla_id,
            color_id=color_id,
            temporada_id=temporada_id,
            coleccion_id=coleccion_id,
            genero=genero,
            marca=marca,
            precio_min=precio_min,
            precio_max=precio_max,
            solo_activos=solo_activos,
            limit=limit,
            offset=offset,
            codigo_hex=codigo_hex
        )
        result = []
        for p in productos:
            imagenes = await self.producto_repo.listarImagenesPorProducto(p.id)
            temporada_ids = await self.producto_repo.listarTemporadaIds(p.id)
            coleccion_ids = await self.producto_repo.listarColeccionIds(p.id)
            from backend.app.schemas.catalogo_maestros import ImagenProductoDTO
            result.append(ProductoDTO(
                id=p.id,
                categoria_id=p.categoria_id,
                proveedor_principal_id=p.proveedor_principal_id,
                nombre=p.nombre,
                descripcion=p.descripcion,
                genero=p.genero,
                marca=p.marca,
                precio_base=p.precio_base,
                activo=p.activo,
                creado_en=p.creado_en,
                actualizado_en=p.actualizado_en,
                imagenes=[ImagenProductoDTO.model_validate(i) for i in imagenes],
                temporada_ids=temporada_ids,
                coleccion_ids=coleccion_ids
            ))
        return result
