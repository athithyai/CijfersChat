"""LLM-powered intent planner.

Responsibilities
----------------
- Accept natural-language user messages
- Build a context-rich system prompt using the CBS catalog
- Call an OpenAI-compatible LLM (GPT-4o or Ollama)
- Extract and validate the JSON plan
- Retry once if the plan fails Pydantic validation
- NEVER execute queries, fetch data, or render anything

The planner is purely declarative — it produces a MapPlan; all execution
happens in the backend services.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from catalog_index import CatalogIndex, _PRIORITY_TABLES
from config import get_settings
from models import MapPlan

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Gemeente name → code lookup (most-requested cities) ──────────────────────
_GEMEENTE_CODES: dict[str, str] = {
    "amsterdam": "GM0363",
    "rotterdam": "GM0599",
    "den haag": "GM0518",
    "the hague": "GM0518",
    "utrecht": "GM0344",
    "eindhoven": "GM0772",
    "groningen": "GM0014",
    "tilburg": "GM0855",
    "almere": "GM0034",
    "breda": "GM0758",
    "nijmegen": "GM0268",
    "enschede": "GM0153",
    "haarlem": "GM0392",
    "arnhem": "GM0202",
    "zaanstad": "GM0479",
    "amersfoort": "GM0307",
    "apeldoorn": "GM0200",
    "s-hertogenbosch": "GM0796",
    "den bosch": "GM0796",
    "zwolle": "GM0193",
    "leiden": "GM0546",
    "maastricht": "GM0935",
    "dordrecht": "GM0505",
    "zoetermeer": "GM0637",
    "deventer": "GM0150",
    "delft": "GM0503",
    "alkmaar": "GM0361",
    "leeuwarden": "GM0080",
    "venlo": "GM0983",
    "emmen": "GM0114",
}

# ── System prompt template ────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a spatial data query planner for Dutch regional statistics (CBS StatLine).
Your ONLY job is to convert the user's natural-language question into a structured JSON plan.
You must NOT execute queries, fetch data, or explain how to code anything.

=== APPROVED CBS TABLES (use ONLY these) ===
{tables_summary}

⚠️  CRITICAL: You MUST use one of the table IDs listed above. Do NOT invent or guess table IDs.
    When in doubt, use "{default_table}" — it is the most comprehensive kerncijfers table.

=== MEASURE CODES FOR {default_table} (kerncijfers wijken en buurten) ===
{measures_summary}

=== GEOGRAPHY LEVELS ===
- gemeente   → whole municipalities (GM#### codes, e.g. GM0363 = Amsterdam)
- wijk       → districts within a municipality (WK###### codes)
- buurt      → neighbourhoods within a wijk (BU######## codes)

=== WELL-KNOWN GEMEENTE CODES ===
{gemeente_codes}

=== OUTPUT FORMAT ===
Output ONLY a single valid JSON object — no markdown, no code fences, no commentary.

{{
  "intent": "map_choropleth",
  "table_id": "<one of the approved table IDs above>",
  "measure_code": "<exact column name from the measure codes list above>",
  "geography_level": "<gemeente|wijk|buurt>",
  "region_scope": "<GM#### or null for all Netherlands>",
  "period": null,
  "classification": "quantile",
  "n_classes": 5,
  "message": "<short user-facing explanation in the same language as the user>"
}}

=== KEYWORD → MEASURE CODE CHEAT SHEET ===
Use these mappings when the user's request matches a topic below:

  house value / WOZ / huiswaarde / woningwaarde / vastgoedwaarde
      → GemiddeldeWOZWaardeVanWoningen_39

  population / bevolking / inwoners / aantal inwoners / residents
      → AantalInwoners_5

  population density / bevolkingsdichtheid / dichtheid
      → Bevolkingsdichtheid_33

  households / huishoudens
      → HuishoudensTotaal_29

  housing stock / woningvoorraad / woningen aantal
      → Woningvoorraad_35

  income / inkomen / average income / gemiddeld inkomen / wealth / vermogen / poverty / armoede
      → table_id MUST be "85984NED" (income data is NOT in 86165NED — that table has nulls)
      → measure_code: GemiddeldInkomenPerInwoner_78
      → other income codes in 85984NED:
           GemiddeldInkomenPerInkomensontvanger_77  (per recipient)
           GemGestandaardiseerdInkomen_83           (standardised household)
           MediaanVermogenVanParticuliereHuish_86   (median wealth)
           PersonenInArmoede_81                     (poverty rate)
      → Note: some buurt rows will be null (CBS suppresses small-area income for privacy)

  owner-occupied / koopwoningen / eigenwoningen
      → Koopwoningen_47

  age 0-15 / kinderen
      → k_0Tot15Jaar_8

  elderly / ouderen / 65+
      → k_65JaarOfOuder_12

=== EXPLAIN INTENT ===
Use intent = "explain" when the user asks to INTERPRET or UNDERSTAND the current map —
not to load new data. Signals: "what does this mean?", "explain", "leg uit", "why is X
so high/low?", "is that a lot?", "which buurt is richest/poorest?", "compare" (when no
new geography or measure is requested).
Keep all other plan fields identical to the current map context.

Template for explain intent:
{{
  "intent": "explain",
  "table_id": "{default_table}",
  "measure_code": "AantalInwoners_5",
  "geography_level": "gemeente",
  "region_scope": null,
  "period": null,
  "classification": "quantile",
  "n_classes": 5,
  "message": ""
}}

=== CONVERSATIONAL MESSAGES ===
If the user is greeting, chatting, or asking what you can do (e.g. "hi", "hello",
"goedemorgen", "what can you show me?", "help", "what data do you have?"), use intent = "info".

For "what can you do" / "help" / "what data do you have", use this exact message:
"I can show interactive choropleth maps of Dutch regional statistics from CBS StatLine.

Try asking me:
• Show average house value by buurt in Utrecht
• Population density across gemeenten in Noord-Holland
• Compare income by wijk in Amsterdam
• Zoom into Rotterdam buurten

I support three geography levels: gemeente (municipality), wijk (district), and buurt (neighbourhood).
Data comes from CBS Kerncijfers wijken en buurten — covering population, housing, income, age groups, and more."

For greetings (hi, hello, goedemorgen), respond warmly in the same language and invite a question.
For thanks / feedback, acknowledge it briefly and invite another question.

Template for info intent:
{{
  "intent": "info",
  "table_id": "{default_table}",
  "measure_code": "AantalInwoners_5",
  "geography_level": "gemeente",
  "region_scope": null,
  "period": null,
  "classification": "quantile",
  "n_classes": 5,
  "message": "<your response here>"
}}

=== RULES ===
1. table_id  MUST be one of the approved table IDs — never use any other.
2. measure_code MUST be one of the exact codes listed in the measure codes section above.
   Do NOT invent codes. Do NOT use title words as codes.
   Use the CHEAT SHEET above first; fall back to the full measure list if not listed.
3. period = null always — these tables are single-year snapshots with no time dimension.
4. region_scope = null → show all Netherlands for the requested level.
5. For wijk or buurt queries about a city, set region_scope to the city's GM code.
6. Default to table_id = "{default_table}" unless another approved table is clearly better.
7. The message field is REQUIRED and must never be empty. Write 1-2 sentences describing
   what the map shows (measure, level, location). Use the same language as the user.
   Example: "Gemiddeld inkomen per inwoner per gemeente in Rotterdam."
8. Output ONLY the JSON object — nothing else.
"""


# ── Client factory ────────────────────────────────────────────────────────────

def _make_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict[str, Any]:
    """Extract and clean the first JSON object from LLM output.

    Handles common small-model quirks:
    - Markdown code fences (```json … ```)
    - JavaScript-style // line comments
    - Trailing commas before } or ]
    - Single-quoted strings (converted to double-quoted)
    """
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip()

    # Find the outermost JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response:\n{text[:300]}")

    raw = match.group()

    # Remove // line comments (not valid JSON but common in LLM output)
    raw = re.sub(r"//[^\n]*", "", raw)

    # Remove /* block comments */
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)

    # Remove trailing commas before } or ] (another common LLM error)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse JSON from LLM response: {exc}\nCleaned text:\n{raw[:400]}"
        ) from exc


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_system_prompt(catalog: CatalogIndex, context: dict | None = None) -> str:
    gemeente_lines = "\n".join(
        f"  {name.title()}: {code}" for name, code in list(_GEMEENTE_CODES.items())[:20]
    )
    # Only show priority tables so the LLM cannot pick anything else
    priority_tables = [t for t in catalog.list_tables() if t.id in _PRIORITY_TABLES]
    tables_lines = "\n".join(
        f"  {t.id}: {t.short_title} ({t.period})" for t in priority_tables
    ) or f"  {settings.DEFAULT_TABLE}: Kerncijfers wijken en buurten (latest)"

    prompt = _SYSTEM_PROMPT.format(
        tables_summary=tables_lines,
        default_table=settings.DEFAULT_TABLE,
        measures_summary=catalog.measures_summary(settings.DEFAULT_TABLE, max_items=25),
        gemeente_codes=gemeente_lines,
    )

    if context:
        scope_str = context.get("region_scope") or "null (all Netherlands)"
        context_block = (
            "\n=== CURRENT MAP CONTEXT (carry over unless user explicitly changes it) ===\n"
            f"  table_id:         {context.get('table_id', settings.DEFAULT_TABLE)}\n"
            f"  measure_code:     {context.get('measure_code', 'AantalInwoners_5')}\n"
            f"  geography_level:  {context.get('geography_level', 'gemeente')}\n"
            f"  region_scope:     {scope_str}\n"
        )
        prompt = context_block + "\n" + prompt

    return prompt


# ── Main public API ───────────────────────────────────────────────────────────

async def generate_plan(
    message: str,
    history: list[dict[str, str]],
    catalog: CatalogIndex,
    context: dict | None = None,
) -> MapPlan:
    """Parse a natural-language message into a validated MapPlan.

    Retries once if the LLM output fails validation.
    """
    client = _make_client()
    system_prompt = _build_system_prompt(catalog, context=context)

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    # Include recent chat history (last 6 turns for context)
    for turn in history[-6:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": message})

    for attempt in range(2):
        logger.info("LLM plan attempt %d for: %r", attempt + 1, message[:80])
        try:
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=600,
                temperature=0.0,
            )
            raw_text = response.choices[0].message.content or ""
            logger.debug("LLM raw output: %s", raw_text[:500])

            plan_dict = _extract_json(raw_text)
            plan = MapPlan.model_validate(plan_dict)
            return plan

        except Exception as exc:
            if attempt == 0:
                logger.warning("Plan attempt 1 failed (%s); retrying …", exc)
                # Inject the error into the conversation so the LLM can self-correct
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous response was invalid: {exc}. "
                            "Please output ONLY a valid JSON object matching the schema."
                        ),
                    }
                )
            else:
                logger.error("Plan generation failed after 2 attempts: %s", exc)
                raise ValueError(f"Could not generate a valid plan: {exc}") from exc

    # Should never reach here
    raise RuntimeError("Unexpected planner state")


async def generate_narration(
    user_message: str,
    plan: "MapPlan",
    meta: dict | None,
    history: list[dict[str, str]],
    measure_label: str,
    top_regions: list[dict] | None = None,
) -> str:
    """Generate a rich conversational reply after data has been fetched.

    This is a second LLM call — separate from the planner — with higher
    temperature for more natural language. Never raises: falls back to a
    template string on any failure.

    Parameters
    ----------
    user_message  : The original user question
    plan          : The executed MapPlan
    meta          : Join metadata (breaks, n_matched, n_total, period) or None
    history       : Recent chat history (last 4 turns used)
    measure_label : Human-readable measure name
    top_regions   : Top-N regions by value (for highlighting interesting points)
    """
    client = _make_client()

    # Language detection: use Dutch if any Dutch signal words are present
    dutch_signals = {
        "nederland", "dutch", "nl", "buurt", "wijk", "gemeente", "wat", "toon",
        "laat", "gemiddeld", "per", "toon", "bereik", "vergelijk", "leg", "uit",
        "waarom", "welke", "hoeveel", "veel", "weinig", "hoog", "laag",
    }
    lang = "Dutch" if any(w in user_message.lower().split() for w in dutch_signals) else "English"

    # Build a compact data summary — kept under 200 tokens
    data_lines: list[str] = []
    if meta and meta.get("n_matched", 0) > 0:
        n_matched = meta["n_matched"]
        n_total   = meta.get("n_total", n_matched)
        breaks    = meta.get("breaks", [])
        period    = meta.get("period", "")

        def _fmt(v: float) -> str:
            if abs(v) >= 1_000_000: return f"{v / 1_000_000:.1f}M"
            if abs(v) >= 1_000: return f"{v:,.0f}"
            if v != int(v): return f"{v:.1f}"
            return str(int(v))

        if len(breaks) >= 2:
            lo, hi = breaks[0], breaks[-1]
            mid_idx = len(breaks) // 2
            approx_median = breaks[mid_idx]
            data_lines.append(f"Measure: {measure_label}")
            data_lines.append(f"Level: {plan.geography_level}")
            if plan.region_scope:
                data_lines.append(f"Scope: {plan.region_scope}")
            data_lines.append(f"Regions with data: {n_matched}/{n_total}")
            data_lines.append(f"Range: {_fmt(lo)} – {_fmt(hi)}")
            data_lines.append(f"Approx. median: {_fmt(approx_median)}")
            if period:
                data_lines.append(f"Reference period: {period}")
            if top_regions:
                region_str = ", ".join(
                    f"{r['statnaam']} ({_fmt(r['value'])})"
                    for r in top_regions[:5]
                    if r.get("value") is not None
                )
                if region_str:
                    data_lines.append(f"Highest values: {region_str}")

    data_summary = "\n".join(data_lines) if data_lines else "No data statistics available."

    system = (
        f"You are a helpful Dutch regional statistics assistant. "
        f"Respond in {lang}. Be conversational and insightful — 2 to 4 sentences. "
        f"Highlight what is interesting or surprising. Do not just list every number. "
        f"Do not repeat the user's question verbatim. Do not use bullet points or markdown.\n\n"
        f"DATA CONTEXT:\n{data_summary}"
    )

    msgs: list[dict[str, str]] = [{"role": "system", "content": system}]
    # Include only the last 4 turns — Narrator needs less context than Planner
    for turn in history[-4:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            msgs.append({"role": turn["role"], "content": turn["content"]})
    msgs.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=msgs,  # type: ignore[arg-type]
            max_tokens=300,
            temperature=0.7,
        )
        result = (response.choices[0].message.content or "").strip()
        if result:
            return result
    except Exception as exc:
        logger.warning("Narrator LLM call failed: %s", exc)

    # Graceful fallback — never crashes
    if data_lines:
        range_line = next((l for l in data_lines if l.startswith("Range:")), "")
        return f"{measure_label} per {plan.geography_level}. {range_line}".strip(" .")
    return f"{measure_label} per {plan.geography_level}."
