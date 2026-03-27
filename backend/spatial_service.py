"""PDOK spatial service — fetches CBS administrative boundary geometries.

Data source
-----------
PDOK OGC API Features (OGC API - Features, Part 1: Core)
  https://api.pdok.nl/cbs/gebiedsindelingen/ogc/v1/

Collections used
----------------
  gemeente_gegeneraliseerd   → GM#### codes
  wijk_gegeneraliseerd       → WK###### codes
  buurt_gegeneraliseerd      → BU######## codes

⚠️ IMPORTANT: This PDOK endpoint does NOT support CQL/OGC filtering.
   The `filter` query parameter returns HTTP 400.
   All server-side filtering is therefore disabled; we filter in Python
   after fetching.  The full collection is cached for 24 h.

Property fields on each feature
---------------------------------
  statcode   — CBS region code, e.g. 'BU03440001'
  statnaam   — Region name, e.g. 'Lombok-West'
  gm_code    — Parent municipality code, e.g. 'GM0344'
  jaarcode   — Boundary year (integer), e.g. 2024
  jrstatcode — Year + statcode combined

Join key
--------
  feature.properties.statcode  ←→  CBS WijkenEnBuurten column (both stripped)
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from cache import cache_get, cache_set, geometry_cache, make_key
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Collection registry ───────────────────────────────────────────────────────

_COLLECTION_MAP: dict[str, str] = {
    "gemeente": "gemeente_gegeneraliseerd",
    "wijk":     "wijk_gegeneraliseerd",
    "buurt":    "buurt_gegeneraliseerd",
}

_PAGE_LIMIT = 100      # PDOK max items per page (server rejects > 100)
_TIMEOUT    = 60.0     # seconds — geometry responses can be large


# ── Main public API ───────────────────────────────────────────────────────────

async def get_geometries(
    geo_level: str,
    region_scope: str | None,
    year: int | None = None,
) -> dict[str, Any]:
    """Fetch GeoJSON FeatureCollection from PDOK.

    The full collection for the geo_level is fetched and cached.
    Client-side filtering narrows it to region_scope when provided.

    Parameters
    ----------
    geo_level    : 'gemeente' | 'wijk' | 'buurt'
    region_scope : GM#### code to narrow to one municipality, or None (all NL)
    year         : Preferred boundary year; latest used if None

    Returns
    -------
    GeoJSON FeatureCollection with properties: statcode, statnaam, gm_code
    """
    collection = _COLLECTION_MAP.get(geo_level)
    if not collection:
        raise ValueError(
            f"Unknown geography level: {geo_level!r}. Use gemeente / wijk / buurt."
        )

    # The full (unfiltered) collection is cached at the level key
    full_cache_key = make_key("geom_full", geo_level)
    features: list[dict] | None = cache_get(geometry_cache, full_cache_key)

    if features is None:
        logger.info(
            "Fetching full PDOK collection '%s' (no server-side filter supported) …",
            collection,
        )
        base_url = f"{settings.PDOK_OGC_BASE}/collections/{collection}/items"
        features = await _fetch_all_pages(base_url)
        cache_set(geometry_cache, full_cache_key, features)
        logger.info("Cached %d raw features for %s", len(features), geo_level)

    # Pick the right boundary year
    effective_year = year or settings.DEFAULT_GEO_YEAR
    year_features  = _filter_by_year(features, effective_year)

    # Client-side scope filter
    scoped = _filter_by_scope(year_features, geo_level, region_scope)

    if not scoped:
        logger.warning(
            "No PDOK features after filtering: level=%s scope=%s year=%s",
            geo_level, region_scope, effective_year,
        )

    geojson = _build_feature_collection(scoped)
    logger.info(
        "Returning %d PDOK features for level=%s scope=%s",
        len(scoped), geo_level, region_scope,
    )
    return geojson


# ── Fetch helpers ─────────────────────────────────────────────────────────────

async def _fetch_all_pages(base_url: str) -> list[dict[str, Any]]:
    """Paginate through PDOK using OGC 'next' links and return all raw features.

    PDOK returns HTTP 400 for:
      - CQL filter parameters
      - Unknown query parameters (including 'offset')
    So we only send 'f' and 'limit' on the first request, then follow
    the 'next' link href verbatim from each response.
    """
    features: list[dict[str, Any]] = []
    next_url: str | None = base_url
    first = True

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        while next_url:
            try:
                if first:
                    resp = await client.get(
                        next_url, params={"f": "json", "limit": str(_PAGE_LIMIT)}
                    )
                    first = False
                else:
                    # Follow the href exactly as PDOK provided it
                    resp = await client.get(next_url)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "PDOK request failed HTTP %d: %s",
                    exc.response.status_code, next_url,
                )
                raise RuntimeError(
                    f"PDOK geometry fetch failed (HTTP {exc.response.status_code})"
                ) from exc

            batch = data.get("features", [])
            features.extend(batch)
            logger.debug(
                "PDOK page  got=%d  total_so_far=%d", len(batch), len(features)
            )

            # Find the 'next' link (OGC API Features standard)
            next_url = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    next_url = link.get("href")
                    break

    return features


# ── Client-side filtering ─────────────────────────────────────────────────────

def _filter_by_year(features: list[dict], year: int) -> list[dict]:
    """Keep features with the requested jaarcode; fall back to latest available."""
    matched = [
        f for f in features
        if f.get("properties", {}).get("jaarcode") == year
    ]
    if matched:
        return matched

    # Fall back to the latest jaarcode present
    jaarcodes = [
        f["properties"]["jaarcode"]
        for f in features
        if f.get("properties", {}).get("jaarcode") is not None
    ]
    if not jaarcodes:
        return features   # no jaarcode info — return everything

    latest = max(jaarcodes)
    if latest != year:
        logger.warning(
            "Boundary year %d not available — using %d. "
            "Cross-year comparisons may not be valid.",
            year, latest,
        )
    return [f for f in features if f.get("properties", {}).get("jaarcode") == latest]


def _filter_by_scope(
    features: list[dict],
    geo_level: str,
    region_scope: str | None,
) -> list[dict]:
    """Filter features client-side by region_scope.

    - gemeente level + GM scope → single municipality by statcode
    - wijk / buurt level + GM scope → all regions whose gm_code matches
    - No scope → return all features
    """
    if region_scope is None:
        return features

    scope = region_scope.strip().upper()

    if geo_level == "gemeente" and scope.startswith("GM"):
        return [
            f for f in features
            if str(f.get("properties", {}).get("statcode", "")).strip().upper() == scope
        ]

    if geo_level in ("wijk", "buurt") and scope.startswith("GM"):
        return [
            f for f in features
            if str(f.get("properties", {}).get("gm_code", "")).strip().upper() == scope
        ]

    # WK scope for buurt: match on statcode prefix
    if geo_level == "buurt" and scope.startswith("WK"):
        return [
            f for f in features
            if str(f.get("properties", {}).get("statcode", "")).strip().upper()
               .startswith(scope[:8])
        ]

    return features


# ── Feature normalisation ─────────────────────────────────────────────────────

def _build_feature_collection(features: list[dict]) -> dict[str, Any]:
    """Build a clean GeoJSON FeatureCollection with only the fields we need."""
    clean: list[dict] = []
    for f in features:
        props   = f.get("properties") or {}
        statcode: str = str(props.get("statcode", "")).strip()
        statnaam: str = str(props.get("statnaam", "")).strip()
        gm_code:  str = str(props.get("gm_code",  "")).strip()
        geom = f.get("geometry")

        if not statcode or geom is None:
            continue

        clean.append({
            "type": "Feature",
            "properties": {
                "statcode": statcode,
                "statnaam": statnaam,
                "gm_code":  gm_code,
            },
            "geometry": geom,
        })

    return {"type": "FeatureCollection", "features": clean}
