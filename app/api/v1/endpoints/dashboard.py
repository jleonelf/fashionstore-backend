"""Presentación Dashboard — CU19 (RF24). Se monta bajo /reportes."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.dependencias import get_usuario_actual
from backend.app.models.seguridad import Usuario
from backend.app.schemas.probador_ia import DashboardDTO
from backend.app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get(
    "/dashboard", response_model=DashboardDTO,
    summary="Dashboard e indicadores (CU19)",
    description="Ventas, ingresos y margen por periodo/sucursal, ticket promedio, top productos, "
    "stock crítico y valorización, conversión de reservas, estados de pedidos y efectividad de "
    "promociones. Fechas UTC, RBAC (ADMIN global; ENCARGADO su sucursal) y respuestas tipadas.",
)
async def consultarDashboard(
    desde: Optional[datetime] = Query(None),
    hasta: Optional[datetime] = Query(None),
    sucursal_id: Optional[uuid.UUID] = Query(None, alias="sucursal"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
) -> DashboardDTO:
    return await DashboardService(db).indicadores(
        usuario, desde=desde, hasta=hasta, sucursal_id=sucursal_id
    )
