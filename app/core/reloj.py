"""Reloj UTC inyectable (Ciclo 2, Entrega 1).

Toda la logica de vigencia usa instantes UTC. Prohibido datetime.utcnow()
en codigo nuevo: usar RelojSistema.ahora() o inyectar RelojFijo en pruebas
(job de expiracion CU24 con reloj simulado).
"""
from datetime import datetime, timedelta, timezone


class RelojSistema:
    """Reloj productivo: siempre UTC con tzinfo."""

    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)


class RelojFijo:
    """Reloj determinista para pruebas: no avanza salvo avance() explicito."""

    def __init__(self, instante: datetime):
        if instante.tzinfo is None:
            instante = instante.replace(tzinfo=timezone.utc)
        self._instante = instante

    def ahora(self) -> datetime:
        return self._instante

    def avanzar(self, delta: timedelta) -> datetime:
        self._instante = self._instante + delta
        return self._instante


def utcnow() -> datetime:
    """Atajo productivo equivalente a RelojSistema().ahora()."""
    return datetime.now(timezone.utc)


def asegurar_utc(instante: datetime) -> datetime:
    """Normaliza un datetime naive a UTC (asume UTC si no tiene tzinfo)."""
    if instante.tzinfo is None:
        return instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(timezone.utc)


# Vigencias RN-03: sin pago 24 h; con adelanto/pago confirmado 72 h.
# Base temporal: creada_en (el pago no mueve la base ni acumula extensiones).
VIGENCIA_SIN_PAGO = timedelta(hours=24)
VIGENCIA_CON_PAGO = timedelta(hours=72)


def calcular_vencimiento(creada_en: datetime, con_pago_confirmado: bool) -> datetime:
    """vence_en = creada_en + 24 h (sin pago) o + 72 h (con pago/adelanto)."""
    base = asegurar_utc(creada_en)
    return base + (VIGENCIA_CON_PAGO if con_pago_confirmado else VIGENCIA_SIN_PAGO)


def vencida(vence_en: datetime, ahora: datetime) -> bool:
    """True si el instante actual alcanzo o supero el vencimiento (UTC)."""
    return asegurar_utc(ahora) >= asegurar_utc(vence_en)
