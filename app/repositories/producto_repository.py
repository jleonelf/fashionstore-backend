import uuid
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.catalogo import Producto, ImagenProducto, ProductoTemporada, ProductoColeccion

class ProductoRepository:
    """
    Datos ProductoRepository.* para CU05 (y base buscarConFiltros para CU06)
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscarPorId(self, producto_id: uuid.UUID) -> Optional[Producto]:
        q = select(Producto).options(selectinload(Producto.imagenes)).where(Producto.id == producto_id)
        result = await self.db.execute(q)
        producto = result.scalars().first()
        if producto:
            # Cargar temporada_ids y coleccion_ids manualmente para no hacer n+1 complejo
            # Se lazy carga vía queries separadas en servicio; aquí solo producto base + imagenes
            pass
        return producto

    async def buscarPorNombre(self, nombre: str) -> Optional[Producto]:
        q = select(Producto).where(Producto.nombre.ilike(nombre.strip()))
        result = await self.db.execute(q)
        return result.scalars().first()

    async def listar(self, solo_activos: bool = False, limit: int = 50, offset: int = 0) -> List[Producto]:
        q = select(Producto).options(selectinload(Producto.imagenes))
        if solo_activos:
            q = q.where(Producto.activo == True)
        q = q.order_by(Producto.nombre).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def crear(self, producto: Producto) -> Producto:
        self.db.add(producto)
        await self.db.flush()
        return producto

    async def actualizar(self, producto: Producto) -> Producto:
        await self.db.flush()
        return producto

    async def buscarConFiltros(
        self,
        texto: Optional[str] = None,
        categoria_id: Optional[uuid.UUID] = None,
        genero: Optional[str] = None,
        marca: Optional[str] = None,
        precio_min: Optional[float] = None,
        precio_max: Optional[float] = None,
        solo_activos: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Producto]:
        """
        CU06 base: filtra productos por categoria, genero, marca, precio, texto.
        Para CU05 solo provee base; CU06 lo ampliará con talla/color/temporada/coleccion.
        """
        q = select(Producto).options(selectinload(Producto.imagenes))
        if solo_activos:
            q = q.where(Producto.activo == True)
        if texto:
            like = f"%{texto.strip()}%"
            q = q.where(or_(Producto.nombre.ilike(like), Producto.descripcion.ilike(like), Producto.marca.ilike(like)))
        if categoria_id:
            q = q.where(Producto.categoria_id == categoria_id)
        if genero:
            q = q.where(Producto.genero.ilike(genero.strip()))
        if marca:
            q = q.where(Producto.marca.ilike(marca.strip()))
        if precio_min is not None:
            q = q.where(Producto.precio_base >= precio_min)
        if precio_max is not None:
            q = q.where(Producto.precio_base <= precio_max)
        q = q.order_by(Producto.nombre).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # Helpers para imágenes y asociaciones
    async def listarImagenesPorProducto(self, producto_id: uuid.UUID) -> List[ImagenProducto]:
        q = select(ImagenProducto).where(ImagenProducto.producto_id == producto_id).order_by(ImagenProducto.orden)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def crearImagen(self, imagen: ImagenProducto) -> ImagenProducto:
        self.db.add(imagen)
        await self.db.flush()
        return imagen

    async def listarTemporadaIds(self, producto_id: uuid.UUID) -> List[uuid.UUID]:
        q = select(ProductoTemporada.temporada_id).where(ProductoTemporada.producto_id == producto_id)
        result = await self.db.execute(q)
        return [row[0] for row in result.all()]

    async def listarColeccionIds(self, producto_id: uuid.UUID) -> List[uuid.UUID]:
        q = select(ProductoColeccion.coleccion_id).where(ProductoColeccion.producto_id == producto_id)
        result = await self.db.execute(q)
        return [row[0] for row in result.all()]

    async def asociarTemporadas(self, producto_id: uuid.UUID, temporada_ids: List[uuid.UUID]):
        # Eliminar anteriores y recrear (para actualizar)
        # Para crear, solo insertar
        for tid in temporada_ids:
            assoc = ProductoTemporada(producto_id=producto_id, temporada_id=tid)
            self.db.add(assoc)
        await self.db.flush()

    async def asociarColecciones(self, producto_id: uuid.UUID, coleccion_ids: List[uuid.UUID]):
        for cid in coleccion_ids:
            assoc = ProductoColeccion(producto_id=producto_id, coleccion_id=cid)
            self.db.add(assoc)
        await self.db.flush()

    async def limpiarTemporadas(self, producto_id: uuid.UUID):
        from sqlalchemy import delete
        await self.db.execute(delete(ProductoTemporada).where(ProductoTemporada.producto_id == producto_id))
        await self.db.flush()

    async def limpiarColecciones(self, producto_id: uuid.UUID):
        from sqlalchemy import delete
        await self.db.execute(delete(ProductoColeccion).where(ProductoColeccion.producto_id == producto_id))
        await self.db.flush()

    async def limpiarImagenes(self, producto_id: uuid.UUID):
        from sqlalchemy import delete
        await self.db.execute(delete(ImagenProducto).where(ImagenProducto.producto_id == producto_id))
        await self.db.flush()
