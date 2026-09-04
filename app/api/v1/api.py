from fastapi import APIRouter
from backend.app.api.v1.endpoints import clientes, sesion, usuarios, roles, ciudades, sucursales, proveedores, recepciones, maestros, productos, variantes

api_router = APIRouter()

api_router.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(sesion.router, prefix="/sesion", tags=["Autenticación"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Gestión de Usuarios"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(ciudades.router, prefix="/ciudades", tags=["Ciudades"])
api_router.include_router(sucursales.router, prefix="/sucursales", tags=["Sucursales y Delivery"])
api_router.include_router(proveedores.router, prefix="/proveedores", tags=["Proveedores"])
api_router.include_router(recepciones.router, prefix="/recepciones", tags=["Recepción de Lotes"])
# CU05 - Maestros, Productos y Variantes
api_router.include_router(maestros.router_tallas, prefix="/tallas", tags=["Maestros - Tallas"])
api_router.include_router(maestros.router_colores, prefix="/colores", tags=["Maestros - Colores"])
api_router.include_router(maestros.router_categorias, prefix="/categorias", tags=["Maestros - Categorías"])
api_router.include_router(maestros.router_temporadas, prefix="/temporadas", tags=["Maestros - Temporadas"])
api_router.include_router(maestros.router_colecciones, prefix="/colecciones", tags=["Maestros - Colecciones"])
api_router.include_router(productos.router, prefix="/productos", tags=["Productos"])
api_router.include_router(variantes.router, prefix="/variantes", tags=["Variantes de Producto"])
