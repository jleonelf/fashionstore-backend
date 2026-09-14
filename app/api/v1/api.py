from fastapi import APIRouter
from backend.app.api.v1.endpoints import clientes, sesion, usuarios, roles, ciudades, sucursales, proveedores, recepciones, maestros, productos, variantes, catalogo, inventario, reservas, pagos, traslados, ventas, devoluciones, reportes

api_router = APIRouter()

api_router.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(sesion.router, prefix="/sesion", tags=["Autenticación"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Gestión de Usuarios"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(ciudades.router, prefix="/ciudades", tags=["Ciudades"])
api_router.include_router(sucursales.router, prefix="/sucursales", tags=["Sucursales y Delivery"])
api_router.include_router(proveedores.router, prefix="/proveedores", tags=["Proveedores"])
api_router.include_router(recepciones.router, prefix="/recepciones", tags=["Recepción de Lotes"])
api_router.include_router(inventario.router, prefix="/inventario", tags=["Inventario Kardex CU07"])
# CU05 - Maestros, Productos y Variantes
api_router.include_router(maestros.router_tallas, prefix="/tallas", tags=["Maestros - Tallas"])
api_router.include_router(maestros.router_colores, prefix="/colores", tags=["Maestros - Colores"])
api_router.include_router(maestros.router_categorias, prefix="/categorias", tags=["Maestros - Categorías"])
api_router.include_router(maestros.router_temporadas, prefix="/temporadas", tags=["Maestros - Temporadas"])
api_router.include_router(maestros.router_colecciones, prefix="/colecciones", tags=["Maestros - Colecciones"])
api_router.include_router(productos.router, prefix="/productos", tags=["Productos"])
api_router.include_router(variantes.router, prefix="/variantes", tags=["Variantes de Producto"])
# CU06 - Catálogo y disponibilidad (RF05, RF07, RF08)
api_router.include_router(catalogo.router, prefix="/catalogo", tags=["Catálogo CU06"])
# Ciclo 2 - Operación en sucursal
api_router.include_router(reservas.router, prefix="/reservas", tags=["Reservas CU08/CU10/CU24"])
api_router.include_router(pagos.router, prefix="/pagos", tags=["Pagos y Adelantos CU11"])
api_router.include_router(traslados.router, prefix="/traslados", tags=["Traslados CU09"])
api_router.include_router(ventas.router, prefix="/ventas", tags=["Venta Presencial CU11"])
api_router.include_router(devoluciones.router_devoluciones, prefix="/devoluciones", tags=["Devoluciones CU12"])
api_router.include_router(devoluciones.router_mermas, prefix="/mermas", tags=["Mermas CU12"])
api_router.include_router(reportes.router, prefix="/reportes", tags=["Reportes CU23"])
