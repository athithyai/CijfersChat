"""CBS StatLine catalog index.

Builds an in-memory lookup of available CBS tables filtered for
geo-statistical relevance (wijken/buurten/kerncijfers).

Usage
-----
    index = await CatalogIndex.build()
    table_id = index.find_table("population", "gemeente")
    measures  = await index.get_measures("86165NED")
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from cache import cache_get, cache_set, make_key, metadata_cache
from cbs_client import get_measure_columns
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# CBS tables known to contain wijk/buurt kerncijfers — checked first
_PRIORITY_TABLES = ["86165NED", "85984NED", "84799NED", "85318NED"]

# Verified measure codes from 86165NED DataProperties (2025 edition)
# Used as fallback hints when the LLM needs guidance
_TOPIC_HINTS: dict[str, list[str]] = {
    "population":    ["AantalInwoners_5"],
    "bevolking":     ["AantalInwoners_5"],
    "inwoners":      ["AantalInwoners_5"],
    "house":         ["GemiddeldWOZWaardeVanWoningen_39"],
    "woz":           ["GemiddeldWOZWaardeVanWoningen_39"],
    "woningwaarde":  ["GemiddeldWOZWaardeVanWoningen_39"],
    "huiswaarde":    ["GemiddeldWOZWaardeVanWoningen_39"],
    "density":       ["Bevolkingsdichtheid_34"],
    "dichtheid":     ["Bevolkingsdichtheid_34"],
    "income":        ["GemiddeldInkomenPerInwoner_78"],
    "inkomen":       ["GemiddeldInkomenPerInwoner_78"],
    "households":    ["Particulierehuishoudens_28"],
    "huishoudens":   ["Particulierehuishoudens_28"],
    "men":           ["Mannen_6"],
    "mannen":        ["Mannen_6"],
    "women":         ["Vrouwen_7"],
    "vrouwen":       ["Vrouwen_7"],
    "youth":         ["k_0Tot15Jaar_8"],
    "jongeren":      ["k_0Tot15Jaar_8"],
    "elderly":       ["k_65JaarOfOuder_12"],
    "ouderen":       ["k_65JaarOfOuder_12"],
}


@dataclass
class TableMeta:
    id: str
    title: str
    short_title: str
    period: str
    geo_levels: list[str] = field(default_factory=list)


class CatalogIndex:
    """In-memory index of CBS geo-statistical tables."""

    def __init__(self, tables: list[TableMeta], measures: dict[str, list[dict[str, str]]]) -> None:
        self._tables = tables
        self._measures = measures  # table_id → [{code, title, unit}]

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    async def build(cls) -> "CatalogIndex":
        """Fetch CBS catalog and build the index. Cached for CACHE_TTL_METADATA seconds."""
        cache_key = make_key("catalog_index")
        if cached := cache_get(metadata_cache, cache_key):
            logger.debug("Returning cached catalog index")
            tables_raw, measures_raw = cached
            tables = [TableMeta(**t) for t in tables_raw]
            return cls(tables, measures_raw)

        logger.info("Building CBS catalog index …")
        tables = await _fetch_geo_tables()
        measures: dict[str, list[dict[str, str]]] = {}

        # Pre-fetch measures for priority tables
        for tid in _PRIORITY_TABLES:
            if any(t.id == tid for t in tables):
                try:
                    measures[tid] = await get_measure_columns(tid)
                except Exception as exc:
                    logger.warning("Could not fetch measures for %s: %s", tid, exc)

        cache_set(
            metadata_cache,
            cache_key,
            ([t.__dict__ for t in tables], measures),
        )
        logger.info("Catalog index built: %d tables", len(tables))
        return cls(tables, measures)

    # ── Public API ────────────────────────────────────────────────────────────

    def find_table(self, topic: str, geo_level: str) -> str:
        """Return the most relevant CBS table ID for a topic and geography level.

        Falls back to DEFAULT_TABLE if nothing matches.
        """
        topic_lower = topic.lower()

        # Priority tables first
        for tid in _PRIORITY_TABLES:
            if any(t.id == tid for t in self._tables):
                return tid  # always try priority tables; they cover most kerncijfers

        # Fuzzy title match
        scored: list[tuple[float, str]] = []
        for t in self._tables:
            score = _title_score(t.short_title.lower(), topic_lower)
            if score > 0:
                scored.append((score, t.id))

        if scored:
            scored.sort(reverse=True)
            return scored[0][1]

        return settings.DEFAULT_TABLE

    def get_measure_hint(self, topic: str, table_id: str) -> str | None:
        """Return a likely measure code for a topic keyword."""
        topic_lower = topic.lower()
        for kw, codes in _TOPIC_HINTS.items():
            if kw in topic_lower:
                # Find which codes actually exist in this table
                available = {m["code"] for m in self._measures.get(table_id, [])}
                for code in codes:
                    if not available or code in available:
                        return code
        return None

    def get_measures(self, table_id: str) -> list[dict[str, str]]:
        """Return measure metadata for a table (may be empty if not pre-fetched)."""
        return self._measures.get(table_id, [])

    def list_tables(self) -> list[TableMeta]:
        return self._tables

    def measures_summary(self, table_id: str, max_items: int = 30) -> str:
        """Return a compact text summary of measures for the LLM prompt."""
        measures = self._measures.get(table_id, [])[:max_items]
        if not measures:
            return "(measure list not available)"
        lines = [f"  {m['code']}: {m['title']} [{m.get('unit', '')}]" for m in measures]
        return "\n".join(lines)

    def tables_summary(self, max_items: int = 10) -> str:
        """Return a compact text summary of available tables for the LLM prompt."""
        rows = self._tables[:max_items]
        lines = [f"  {t.id}: {t.short_title} ({t.period})" for t in rows]
        return "\n".join(lines)


# ── Private helpers ───────────────────────────────────────────────────────────

async def _fetch_geo_tables() -> list[TableMeta]:
    """Fetch CBS OData Catalog and filter for geo-statistical tables."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(settings.CBS_CATALOG_URL)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Could not fetch CBS catalog: %s", exc)
        return _fallback_tables()

    tables: list[TableMeta] = []
    geo_keywords = re.compile(
        r"wijk|buurt|gemeente|kerncijfer|regionaal|regio|gebieden", re.IGNORECASE
    )
    for entry in data.get("value", []):
        title: str = entry.get("ShortTitle", entry.get("Title", ""))
        if not geo_keywords.search(title):
            continue
        tables.append(
            TableMeta(
                id=entry.get("Identifier", ""),
                title=entry.get("Title", ""),
                short_title=title,
                period=entry.get("Period", ""),
                geo_levels=_infer_geo_levels(title),
            )
        )

    if not tables:
        return _fallback_tables()

    # Ensure priority tables are always included
    existing_ids = {t.id for t in tables}
    for tid in _PRIORITY_TABLES:
        if tid not in existing_ids:
            tables.insert(0, TableMeta(id=tid, title=tid, short_title=tid, period="2024"))

    return tables


def _infer_geo_levels(title: str) -> list[str]:
    levels: list[str] = []
    t = title.lower()
    if "gemeente" in t:
        levels.append("gemeente")
    if "wijk" in t:
        levels.append("wijk")
    if "buurt" in t:
        levels.append("buurt")
    return levels or ["gemeente", "wijk", "buurt"]


def _title_score(title: str, query: str) -> float:
    words = query.split()
    return sum(1.0 for w in words if w in title) / max(len(words), 1)


def _fallback_tables() -> list[TableMeta]:
    return [
        TableMeta(
            id="86165NED",
            title="Kerncijfers wijken en buurten 2025",
            short_title="Kerncijfers wijken en buurten 2025",
            period="2025",
            geo_levels=["gemeente", "wijk", "buurt"],
        ),
        TableMeta(
            id="85984NED",
            title="Kerncijfers wijken en buurten 2024",
            short_title="Kerncijfers wijken en buurten 2024",
            period="2024",
            geo_levels=["gemeente", "wijk", "buurt"],
        ),
    ]
