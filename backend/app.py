"""CijfersChat FastAPI application.

Endpoints
---------
GET  /health        → service health check
GET  /catalog       → list of CBS geo-statistical tables
POST /plan          → natural language → MapPlan (no data fetched)
POST /map-data      → MapPlan → enriched GeoJSON
POST /chat          → natural language → MapPlan + enriched GeoJSON + message

The /chat endpoint is the primary integration point for the frontend.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from catalog_index import CatalogIndex, _PRIORITY_TABLES
from cbs_client import get_measure_columns, get_observations
from config import get_settings
from join_engine import join_data_to_geometry
from models import (
    CatalogEntry,
    CatalogResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    MapDataRequest,
    MapDataResponse,
    MapPlan,
    PlanRequest,
)
from planner import generate_plan
from spatial_service import get_geometries

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

catalog: CatalogIndex | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global catalog
    logger.info("Building CBS catalog index …")
    catalog = await CatalogIndex.build()
    logger.info("Catalog ready — %d tables indexed", len(catalog.list_tables()))
    yield
    logger.info("Shutting down CijfersChat backend")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="CijfersChat API",
    description="Chat-with-Map for Dutch regional statistics (CBS + PDOK)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────────────────────

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.3f}s"
    return response


# ── Error handler ─────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)[:200]}"},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

_DEFAULT_MEASURE = "AantalInwoners_5"   # always present in kerncijfers tables

# Human-readable labels for common measure codes (Dutch)
_MEASURE_LABELS: dict[str, str] = {
    "AantalInwoners_5":                       "Aantal inwoners",
    "Bevolkingsdichtheid_33":                 "Bevolkingsdichtheid",
    "Bevolkingsdichtheid_34":                 "Bevolkingsdichtheid",
    "GemiddeldeWOZWaardeVanWoningen_39":      "Gemiddelde WOZ-waarde van woningen",
    "GemiddeldInkomenPerInwoner_78":          "Gemiddeld inkomen per inwoner",
    "GemiddeldInkomenPerInkomensontvanger_77":"Gemiddeld inkomen per ontvanger",
    "GemGestandaardiseerdInkomen_83":         "Gestandaardiseerd inkomen",
    "MediaanVermogenVanParticuliereHuish_86": "Mediaan vermogen",
    "PersonenInArmoede_81":                   "Personen in armoede",
    "Woningvoorraad_35":                      "Woningvoorraad",
    "Koopwoningen_47":                        "Koopwoningen",
    "HuishoudensTotaal_29":                   "Huishoudens",
    "k_0Tot15Jaar_8":                         "Kinderen (0-15 jaar)",
    "k_65JaarOfOuder_12":                     "Ouderen (65+)",
    "Nettoarbeidsparticipatie_71":            "Nettoarbeidsparticipatie",
}

# GM code → city name for the most-queried cities
_GM_NAMES: dict[str, str] = {
    "GM0363": "Amsterdam",   "GM0599": "Rotterdam",  "GM0518": "Den Haag",
    "GM0344": "Utrecht",     "GM0772": "Eindhoven",  "GM0014": "Groningen",
    "GM0855": "Tilburg",     "GM0034": "Almere",     "GM0758": "Breda",
    "GM0268": "Nijmegen",    "GM0153": "Enschede",   "GM0392": "Haarlem",
    "GM0202": "Arnhem",      "GM0307": "Amersfoort", "GM0200": "Apeldoorn",
    "GM0796": "Den Bosch",   "GM0193": "Zwolle",     "GM0546": "Leiden",
    "GM0935": "Maastricht",  "GM0503": "Delft",
}


def _build_message(plan: "MapPlan", meta: dict | None = None) -> str:
    """Generate a readable Dutch assistant message from the plan + optional join stats."""
    measure  = _MEASURE_LABELS.get(plan.measure_code, plan.measure_code.replace("_", " "))
    level    = plan.geography_level
    scope    = plan.region_scope
    location = _GM_NAMES.get(scope, scope) if scope else "Nederland"

    base = f"{measure} per {level} in {location}."

    if meta:
        n_matched = meta.get("n_matched", 0)
        n_total   = meta.get("n_total", 0)
        breaks    = meta.get("breaks", [])

        if n_matched > 0 and len(breaks) >= 2:
            lo  = breaks[0]
            hi  = breaks[-1]

            def fmt(v: float) -> str:
                if abs(v) >= 1_000_000:
                    return f"{v/1_000_000:.1f}M"
                if abs(v) >= 1_000:
                    return f"{v:,.0f}".replace(",", "\u202f")
                if v != int(v):
                    return f"{v:.1f}"
                return str(int(v))

            coverage = ""
            if n_matched < n_total:
                coverage = f" ({n_matched} van {n_total} regio's hebben data)"

            return (
                f"{base}\n"
                f"Bereik: {fmt(lo)} – {fmt(hi)}{coverage}."
            )

        if n_matched == 0:
            return f"{base}\nGeen data beschikbaar voor deze selectie."

    return base

def _fallback_measure(requested: str, available: set[str]) -> str:
    """Return the closest available measure or the safe default."""
    # Try a prefix match (e.g. LLM stripped a suffix number)
    prefix = requested.split("_")[0].lower()
    for code in sorted(available):
        if code.lower().startswith(prefix):
            return code
    return _DEFAULT_MEASURE


def _require_catalog() -> CatalogIndex:
    if catalog is None:
        raise HTTPException(status_code=503, detail="Catalog not yet initialised; try again shortly.")
    return catalog


async def _execute_plan(plan: MapPlan) -> tuple[dict[str, Any], list[str]]:
    """Run a MapPlan end-to-end and return (enriched_geojson, warnings)."""
    all_warnings: list[str] = []

    # 1. Fetch CBS observations
    try:
        df = await get_observations(
            table_id=plan.table_id,
            measure_code=plan.measure_code,
            geography_level=plan.geography_level,
            region_scope=plan.region_scope,
            period=plan.period,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if df.empty:
        all_warnings.append(
            f"No data returned for measure '{plan.measure_code}' in table '{plan.table_id}'. "
            "Check that the measure code is valid."
        )

    # 2. Fetch PDOK geometry
    try:
        geojson = await get_geometries(
            geo_level=plan.geography_level,
            region_scope=plan.region_scope,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if not geojson.get("features"):
        all_warnings.append("No boundary geometries returned from PDOK.")

    # 3. Join CBS data with geometry
    enriched, join_warnings = join_data_to_geometry(
        geojson=geojson,
        df=df,
        measure_code=plan.measure_code,
        classification=plan.classification,
        n_classes=plan.n_classes,
    )
    all_warnings.extend(join_warnings)

    return enriched, all_warnings


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse()


@app.get("/catalog", response_model=CatalogResponse, tags=["catalog"])
async def get_catalog():
    """List available CBS geo-statistical tables."""
    cat = _require_catalog()
    entries = [
        CatalogEntry(
            id=t.id,
            title=t.title,
            period=t.period,
            geo_levels=t.geo_levels,
        )
        for t in cat.list_tables()
    ]
    return CatalogResponse(tables=entries)


@app.post("/plan", response_model=MapPlan, tags=["planning"])
async def plan_endpoint(body: PlanRequest):
    """Convert a natural-language message to a structured MapPlan (no data fetched)."""
    cat = _require_catalog()
    try:
        plan = await generate_plan(body.message, body.history, cat)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return plan


@app.get("/boundaries", tags=["data"])
async def boundaries_endpoint(
    level: str = "gemeente",
    scope: str | None = None,
):
    """Return PDOK boundary geometry only — no CBS data, no choropleth colours.

    Fast: geometry is cached 24 h after the first fetch.
    Used by the layer-toggle buttons on the map.
    """
    if level not in ("gemeente", "wijk", "buurt"):
        raise HTTPException(status_code=422, detail="level must be gemeente, wijk or buurt")
    try:
        geojson = await get_geometries(geo_level=level, region_scope=scope or None)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return geojson


@app.post("/map-data", response_model=MapDataResponse, tags=["data"])
async def map_data_endpoint(body: MapDataRequest):
    """Execute a MapPlan and return enriched GeoJSON."""
    enriched, warnings = await _execute_plan(body.plan)
    return MapDataResponse(
        geojson=enriched,
        message=body.plan.message,
        warnings=warnings,
    )


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat_endpoint(body: ChatRequest):
    """Primary chat endpoint: NL message → plan + enriched GeoJSON + assistant message.

    Flow
    ----
    1. Generate MapPlan from LLM
    2. Fetch CBS observations
    3. Fetch PDOK geometries
    4. Join and enrich GeoJSON
    5. Return everything to the frontend
    """
    cat = _require_catalog()

    # Step 1: Plan
    try:
        plan = await generate_plan(body.message, body.history, cat)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Planning failed: {exc}")

    # Guard: ONLY allow priority (kerncijfers) tables.
    # Any other table the LLM picks is silently replaced with the default so
    # the measure codes in the system prompt always match the table being queried.
    if plan.table_id not in _PRIORITY_TABLES:
        logger.warning(
            "LLM chose non-priority table '%s'; falling back to %s",
            plan.table_id, settings.DEFAULT_TABLE,
        )
        plan = plan.model_copy(update={"table_id": settings.DEFAULT_TABLE})

    logger.info(
        "Plan: table=%s measure=%s level=%s scope=%s",
        plan.table_id, plan.measure_code, plan.geography_level, plan.region_scope,
    )

    # Guard: verify measure_code exists in the chosen table; fall back to a
    # known-good default if the LLM invented a non-existent column name.
    try:
        valid_codes = {m["code"] for m in await get_measure_columns(plan.table_id)}
        if valid_codes and plan.measure_code not in valid_codes:
            fallback = _fallback_measure(plan.measure_code, valid_codes)
            logger.warning(
                "measure_code '%s' not in table %s; using '%s'",
                plan.measure_code, plan.table_id, fallback,
            )
            plan = plan.model_copy(update={"measure_code": fallback})
    except Exception as exc:
        logger.warning("Could not validate measure_code: %s", exc)

    # Conversational / info intent → skip map execution entirely
    if plan.intent == "info":
        logger.info("Info intent — returning message without map data")
        if not plan.message:
            plan = plan.model_copy(update={"message": _build_message(plan)})
        return ChatResponse(
            message=plan.message,
            plan=plan,
            geojson={"type": "FeatureCollection", "features": []},
            warnings=[],
        )

    # At gemeente level a GM scope would return only 1 polygon — not useful for a
    # choropleth. Fetch ALL gemeenten but keep region_scope in the plan so the
    # frontend can zoom to / highlight the requested gemeente.
    fetch_scope = None if plan.geography_level == "gemeente" else plan.region_scope

    # Steps 2–4: Fetch + join (using fetch_scope, not plan.region_scope)
    enriched, warnings = await _execute_plan(
        plan.model_copy(update={"region_scope": fetch_scope})
    )

    # Build the assistant reply — use LLM message if provided, otherwise generate
    # a data-aware description using actual min/max/coverage from the join result
    meta = enriched.get("meta") if isinstance(enriched, dict) else None
    if plan.message:
        reply = plan.message
        # Append data stats even when LLM wrote a message
        if meta and meta.get("n_matched", 0) > 0:
            breaks = meta.get("breaks", [])
            if len(breaks) >= 2:
                def _fmt(v: float) -> str:
                    if abs(v) >= 1_000_000: return f"{v/1_000_000:.1f}M"
                    if abs(v) >= 1_000: return f"{v:,.0f}".replace(",", "\u202f")
                    if v != int(v): return f"{v:.1f}"
                    return str(int(v))
                n_m, n_t = meta["n_matched"], meta["n_total"]
                cov = f" ({n_m}/{n_t} regio's)" if n_m < n_t else ""
                reply += f"\n\nBereik: {_fmt(breaks[0])} – {_fmt(breaks[-1])}{cov}."
    else:
        reply = _build_message(plan, meta)

    return ChatResponse(
        message=reply,
        plan=plan,
        geojson=enriched,
        warnings=warnings,
    )
