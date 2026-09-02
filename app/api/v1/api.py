from fastapi import APIRouter
from backend.app.api.v1.endpoints import clientes, sesion

api_router = APIRouter()

api_router.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(sesion.router, prefix="/sesion", tags=["Autenticación"])
