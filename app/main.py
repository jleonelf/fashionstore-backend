import sys
from pathlib import Path

# Permitir ejecucion tanto desde la raiz como desde dentro de /backend
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from backend.app.core.config import settings
from backend.app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.EXPIRACION_JOB_ACTIVO:
        from backend.app.core.tareas import iniciar_scheduler

        iniciar_scheduler(settings.EXPIRACION_JOB_MINUTOS)
    yield
    if settings.EXPIRACION_JOB_ACTIVO:
        from backend.app.core.tareas import detener_scheduler

        detener_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API RESTful de FashionStore - Plataforma de Comercio Electrónico Omnicanal con Vestidor Virtual e IA",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configuración CORS para Angular Web y Flutter Móvil
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(Exception)
async def error_interno_no_controlado(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})

@app.get("/health", tags=["Salud"])
async def verificar_salud():
    return {
        "estado": "operativo",
        "servicio": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "zona_horaria_negocio": settings.BUSINESS_TIMEZONE,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
