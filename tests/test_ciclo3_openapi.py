"""Corrección 8 — OpenAPI completo: errores de negocio + comparación canónica."""
import json
from pathlib import Path


def _spec():
    import app  # noqa: F401
    from backend.app.main import app as fastapi_app
    return fastapi_app.openapi()


def test_errores_documentados_carrito_checkout():
    spec = _spec()
    op = spec["paths"]["/api/v1/carritos/mio/checkout"]["post"]
    for codigo in ("400", "401", "403", "404", "409", "422"):
        assert codigo in op["responses"], f"checkout debe documentar {codigo}"
    op2 = spec["paths"]["/api/v1/carritos/mio/lineas"]["post"]
    assert "409" in op2["responses"] and "422" in op2["responses"]


def test_errores_stripe_y_decart():
    spec = _spec()
    inten = spec["paths"]["/api/v1/pagos/stripe/intenciones"]["post"]
    for codigo in ("400", "401", "403", "404", "409", "502", "503"):
        assert codigo in inten["responses"], f"stripe intenciones debe documentar {codigo}"
    aut = spec["paths"]["/api/v1/probador/autorizaciones"]["post"]
    for codigo in ("401", "403", "404", "409", "422", "429", "502", "503"):
        assert codigo in aut["responses"], f"decart debe documentar {codigo}"
    # Idempotency-Key documentado en la descripción.
    assert "Idempotency-Key" in aut.get("description", "")


def test_openapi_coincide_con_exportado():
    spec = _spec()
    ruta = Path(__file__).resolve().parent.parent.parent / "docu_general" / "ciclo-3" / "openapi-ciclo3.json"
    assert ruta.exists(), f"falta {ruta}"
    exportado = json.loads(ruta.read_text(encoding="utf-8"))
    canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)
    assert canon(exportado) == canon(spec), "openapi-ciclo3.json desincronizado: regenere con app.openapi()"
