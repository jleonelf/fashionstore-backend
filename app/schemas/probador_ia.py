"""Schemas CU17 — Probador Decart Lucy 2.5 (RF13) e IA (RF25) + Dashboard (RF24)."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

CONSENTIMIENTO_VIGENTE = "decart-v1"


class PruebaVirtualDTO(BaseModel):
    variante_id: uuid.UUID
    compatible: bool
    imagen_prenda_url: str
    prompt_prenda: str
    proveedor: str = "DECART"
    modelo: str = "lucy-2.5"
    aviso_orientativo: str = (
        "Visualización orientativa; no garantiza talla, color, reproducción exacta ni ajuste físico."
    )


class AutorizacionCrearDTO(BaseModel):
    variante_id: uuid.UUID
    consentimiento_version: str = Field(..., description="Debe ser 'decart-v1'")


class AutorizacionDTO(BaseModel):
    client_token: str
    expires_at: datetime
    modelo: str = "lucy-2.5"
    max_session_duration_seconds: int = 120
    imagen_prenda_url: str
    prompt_prenda: str


class NavegacionCrearDTO(BaseModel):
    evento: Literal["VISTA", "PRUEBA_VIRTUAL", "CARRITO", "COMPRA", "BUSQUEDA"] = Field(
        ..., description="Evento sanitizado; nunca incluye contenido audiovisual"
    )
    variante_id: Optional[uuid.UUID] = None
    producto_id: Optional[uuid.UUID] = None


class RecomendacionPedirDTO(BaseModel):
    limite: int = Field(5, ge=1, le=20)
    categoria: Optional[str] = None
    talla: Optional[str] = None


class RecomendacionItemDTO(BaseModel):
    producto_id: uuid.UUID
    variante_id: uuid.UUID
    nombre: str
    precio: Decimal
    disponible: int
    motivo: str


class RecomendacionRespuestaDTO(BaseModel):
    items: List[RecomendacionItemDTO]
    proveedor: str = "DETERMINISTA"


class BusquedaVozDTO(BaseModel):
    texto: str = Field(..., min_length=2, max_length=500)


class BusquedaRespuestaDTO(BaseModel):
    filtros: dict
    total: int
    items: List[RecomendacionItemDTO]
    proveedor: str = "DETERMINISTA"


class ReportePedirDTO(BaseModel):
    consulta: str = Field(..., min_length=4, max_length=500)


class ReporteRespuestaDTO(BaseModel):
    funcion_usada: str
    parametros: dict
    datos: dict
    narrativa: str
    proveedor: str = "DETERMINISTA"


class DecisionPedirDTO(BaseModel):
    dias_ventana: int = Field(30, ge=7, le=180)
    umbral_rotacion: int = Field(2, ge=0, le=100)


class DecisionItemDTO(BaseModel):
    variante_id: uuid.UUID
    sku: str
    accion: Literal["PROMOCION", "LIQUIDACION", "TRASLADO", "REPOSICION", "MANTENER"]
    detalle: str
    stock_total: int
    ventas_periodo: int
    reposicion_sugerida: int = 0


class DecisionRespuestaDTO(BaseModel):
    items: List[DecisionItemDTO]
    proveedor: str = "DETERMINISTA"


class DashboardDTO(BaseModel):
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
    ventas_total: int
    ingresos_total: Decimal
    margen_bruto_total: Decimal
    ticket_promedio: Decimal
    por_sucursal: List[dict] = Field(default_factory=list)
    top_productos: List[dict] = Field(default_factory=list)
    stock_critico: List[dict] = Field(default_factory=list)
    valorizacion_total: Decimal = Decimal("0")
    conversion_reservas: dict = Field(default_factory=dict)
    estados_pedidos: dict = Field(default_factory=dict)
    efectividad_promociones: dict = Field(default_factory=dict)
