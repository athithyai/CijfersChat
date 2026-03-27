"""Pydantic request/response models shared across the application."""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Plan ─────────────────────────────────────────────────────────────────────

class MapPlan(BaseModel):
    """Structured execution plan produced by the LLM planner.

    The LLM fills this; backend services execute it.
    """

    intent: Literal["map_choropleth", "zoom", "compare", "info"] = "map_choropleth"
    table_id: str = Field(..., description="CBS table ID, e.g. '86165NED'")
    measure_code: str = Field(..., description="CBS column name, e.g. 'AantalInwoners_5'")
    geography_level: Literal["gemeente", "wijk", "buurt"]
    region_scope: str | None = Field(
        None,
        description="CBS region code to scope results, e.g. 'GM0363'. None = all Netherlands.",
    )
    period: str | None = Field(
        None,
        description="Ignored — kerncijfers tables are single-year snapshots.",
    )
    classification: Literal["quantile", "equal", "jenks"] = "quantile"
    n_classes: int = Field(5, ge=3, le=9)
    message: str = Field(..., description="Short user-facing explanation in Dutch or English.")

    # ── Field validators ─────────────────────────────────────────────────────

    @field_validator("measure_code", mode="before")
    @classmethod
    def sanitize_measure_code(cls, v: str) -> str:
        """Strip whitespace and reject codes containing spaces, slashes or operators.

        The LLM occasionally outputs formulas like 'A_1 / B_2'.
        We take only the first valid token (word chars + underscore).
        """
        v = str(v).strip()
        # Extract the first valid CBS column token: word chars and underscores only
        match = re.match(r"^([A-Za-z_]\w*)", v)
        if match:
            return match.group(1)
        raise ValueError(
            f"measure_code '{v}' is not a valid CBS column name. "
            "Use an exact key from DataProperties (e.g. 'AantalInwoners_5')."
        )

    @field_validator("table_id", mode="before")
    @classmethod
    def sanitize_table_id(cls, v: str) -> str:
        """Accept only alphanumeric CBS table IDs."""
        v = str(v).strip()
        if not re.match(r"^[A-Za-z0-9]+$", v):
            raise ValueError(f"table_id '{v}' is not a valid CBS table identifier.")
        return v

    @field_validator("message", mode="before")
    @classmethod
    def require_message(cls, v: str) -> str:
        """Reject empty messages — app.py will generate a fallback if needed."""
        return str(v).strip()   # keep even if empty; app.py fills it in

    @field_validator("region_scope", mode="before")
    @classmethod
    def sanitize_region_scope(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if v.lower() in ("null", "none", ""):
            return None
        # Must start with GM / WK / BU followed by digits
        if not re.match(r"^(GM|WK|BU)\d+$", v, re.IGNORECASE):
            return None   # silently drop invalid scope rather than crash
        return v.upper()

    # ── Cross-field validator ─────────────────────────────────────────────────

    @model_validator(mode="after")
    def validate_scope_level(self) -> "MapPlan":
        """Ensure region_scope prefix is consistent with geography_level."""
        if self.region_scope and self.region_scope.startswith("BU"):
            # Buurt-scoped region makes no sense for a buurt-level map; widen to NL
            self.region_scope = None
        return self


# ── API Requests ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)


class PlanRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


class MapDataRequest(BaseModel):
    plan: MapPlan


# ── API Responses ─────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    message: str
    plan: MapPlan
    geojson: dict[str, Any]          # GeoJSON FeatureCollection
    warnings: list[str] = Field(default_factory=list)


class MapDataResponse(BaseModel):
    geojson: dict[str, Any]
    message: str
    warnings: list[str] = Field(default_factory=list)


class CatalogEntry(BaseModel):
    id: str
    title: str
    period: str
    geo_levels: list[str]


class CatalogResponse(BaseModel):
    tables: list[CatalogEntry]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
