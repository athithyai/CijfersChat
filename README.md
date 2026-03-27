<div align="center">

# 🗺️ CijfersChat

### Chat with Dutch regional statistics — on a live map

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![MapLibre GL](https://img.shields.io/badge/MapLibre_GL-4.x-396CB2?style=flat&logo=maplibre&logoColor=white)](https://maplibre.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.x-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<br/>

> Type a plain-language question → get an interactive choropleth map of the Netherlands

**"Show average house value by buurt in Utrecht"**
**"Vergelijk bevolkingsdichtheid per gemeente in Noord-Holland"**
**"Inkomen per wijk in Amsterdam"**

</div>

---

## ✨ Features

| | |
|---|---|
| 🧠 **LLM-powered intent parsing** | Natural language → structured JSON plan, no hardcoded queries |
| 🗺️ **Live choropleth maps** | Gemeente · Wijk · Buurt levels with smooth transitions |
| 📊 **CBS StatLine integration** | Direct OData v3 queries against official Dutch statistics |
| 🏘️ **PDOK boundary service** | Real-time administrative boundaries, always up-to-date |
| 🖱️ **Interactive selection** | Click any polygon → ask a follow-up question about it |
| 🌗 **Dark / light mode** | Fully themed UI |
| 🔌 **Any OpenAI-compatible LLM** | Ollama (free, local) · OpenAI · Groq · Azure OpenAI |
| ⚡ **Layered caching** | Geometry cached 24 h · Statistics cached 15 min |

---

## 📸 Demo

```
User  ›  Show population density by gemeente

      ┌──────────────────────────────────────────────────────┐
      │  💬 Chat                  🗺️  Map                    │
      │  ─────────────────        ─────────────────────────  │
      │  You: Show population     [Choropleth of NL with      │
      │  density by gemeente      colour-coded gemeenten]     │
      │                                                        │
      │  Assistant:               Legend                       │
      │  Bevolkingsdichtheid      ████ 0 – 500 /km²           │
      │  per gemeente voor        ████ 500 – 1 500 /km²       │
      │  Nederland. Bereik:       ████ 1 500 – 3 000 /km²     │
      │  13 – 6 897 (342          ████ 3 000 – 6 000 /km²     │
      │  gemeenten).              ████ > 6 000 /km²            │
      └──────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CijfersChat                                │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    Frontend (React + Vite)                     │  │
│  │                                                                 │  │
│  │   ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │  │
│  │   │  ChatPanel   │    │   MapPanel   │    │   MapControls   │  │  │
│  │   │  ─────────── │    │  ─────────── │    │  ─────────────  │  │  │
│  │   │  Message     │    │  MapLibre GL │    │  Layer toggle   │  │  │
│  │   │  history     │    │  Choropleth  │    │  GM · WK · BU   │  │  │
│  │   │  Plan card   │    │  Legend      │    │  Boundaries     │  │  │
│  │   │  Input bar   │    │  Tooltip     │    │  only mode      │  │  │
│  │   └──────┬───────┘    └──────┬───────┘    └─────────────────┘  │  │
│  │          │                   │                                   │  │
│  │          └────────┬──────────┘  Zustand store                   │  │
│  └───────────────────┼────────────────────────────────────────────┘  │
│                       │  HTTP (REST JSON)                             │
│  ┌────────────────────┼────────────────────────────────────────────┐  │
│  │                FastAPI Backend                                   │  │
│  │                       │                                          │  │
│  │  POST /chat           ▼                                          │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │                    planner.py                               │ │  │
│  │  │  User message ──► LLM (Ollama / OpenAI / Groq)            │ │  │
│  │  │                         │                                   │ │  │
│  │  │                         ▼                                   │ │  │
│  │  │              Structured JSON Plan                           │ │  │
│  │  │  { table_id, measure_code, geography_level, region_scope } │ │  │
│  │  └──────────────────────────┬──────────────────────────────── ┘ │  │
│  │                              │                                    │  │
│  │              ┌───────────────┼───────────────┐                   │  │
│  │              ▼               ▼               ▼                   │  │
│  │  ┌────────────────┐ ┌──────────────┐ ┌───────────────┐          │  │
│  │  │ catalog_index  │ │  cbs_client  │ │spatial_service│          │  │
│  │  │ ────────────── │ │ ──────────── │ │ ────────────  │          │  │
│  │  │ CBS table      │ │ OData v3     │ │ PDOK OGC API  │          │  │
│  │  │ metadata index │ │ queries with │ │ GeoJSON       │          │  │
│  │  │ Topic/measure  │ │ $select      │ │ boundaries    │          │  │
│  │  │ lookup         │ │ $filter      │ │ pagination    │          │  │
│  │  └────────────────┘ └──────┬───────┘ └──────┬────────┘          │  │
│  │                             │                │                    │  │
│  │                             └───────┬────────┘                   │  │
│  │                                     ▼                             │  │
│  │                            ┌─────────────────┐                   │  │
│  │                            │  join_engine.py  │                   │  │
│  │                            │ ─────────────── │                   │  │
│  │                            │ CBS df ⋈ PDOK   │                   │  │
│  │                            │ Quantile / equal│                   │  │
│  │                            │ classification  │                   │  │
│  │                            │ GeoJSON + meta  │                   │  │
│  │                            └────────┬────────┘                   │  │
│  └─────────────────────────────────────┼──────────────────────────┘  │
│                                         │  Enriched GeoJSON           │
└─────────────────────────────────────────┼──────────────────────────── ┘
                                          ▼
                              React renders choropleth
```

---

## 🗂️ Data Sources

### CBS StatLine — Statistics

| | |
|---|---|
| **Provider** | Centraal Bureau voor de Statistiek (CBS) |
| **API** | OData v3 — `https://opendata.cbs.nl/ODataFeed/odata/` |
| **Auth** | None required |
| **License** | CC BY 4.0 |
| **Key tables** | See table below |

#### Priority CBS Tables

| Table ID | Title | Year | Notes |
|----------|-------|------|-------|
| `86165NED` | Kerncijfers wijken en buurten 2025 | 2025 | Default |
| `85984NED` | Kerncijfers wijken en buurten 2024 | 2024 | Income data |
| `84799NED` | Kerncijfers wijken en buurten 2022 | 2022 | |
| `85318NED` | Kerncijfers wijken en buurten 2023 | 2023 | |

#### Key Measure Codes (`86165NED`)

| Code | Dutch label | Unit |
|------|-------------|------|
| `AantalInwoners_5` | Aantal inwoners | persons |
| `Bevolkingsdichtheid_33` | Bevolkingsdichtheid | /km² |
| `GemiddeldeHuishoudensgrootte_28` | Gem. huishoudensgrootte | persons |
| `GemiddeldInkomenPerInwoner_66` | Gem. inkomen per inwoner | × €1 000 |
| `GemiddeldeWOZWaardeVanWoningen_39` | Gem. WOZ-waarde woningen | × €1 000 |
| `Koopwoningen_50` | Koopwoningen | % |
| `HuurwoningenTotaal_51` | Huurwoningen totaal | % |
| `OmgevingsadressendichtheidGem_105` | Omgevingsadressendichtheid | /km² |

---

### PDOK — Boundaries

| | |
|---|---|
| **Provider** | Publieke Dienstverlening Op de Kaart (PDOK) |
| **API** | OGC API Features — `https://api.pdok.nl/cbs/gebiedsindelingen/ogc/v1/` |
| **Auth** | None required |
| **License** | CC BY 4.0 |
| **Collections** | `gemeente_gegeneraliseerd` · `wijk_gegeneraliseerd` · `buurt_gegeneraliseerd` |

#### Geographic Levels

| Level | CBS code | PDOK field | Count (2024) | Example |
|-------|----------|------------|--------------|---------|
| Gemeente | `GM####` | `statcode` | 342 | `GM0363` Amsterdam |
| Wijk | `WK######` | `statcode` | ~3 000 | `WK036300` |
| Buurt | `BU########` | `statcode` | ~12 000 | `BU03630000` |

> ⚠️ PDOK does not support server-side CQL filtering. All boundary filtering is performed client-side after fetching the full collection. Geometry collections are cached for 24 hours.

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 20 LTS+ | [nodejs.org](https://nodejs.org) |
| Ollama *(free)* | latest | [ollama.com](https://ollama.com) |

### 1 · Clone

```bash
git clone https://github.com/athithyai/CijfersChat.git
cd CijfersChat
```

### 2 · Configure

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

The default `.env` points to Ollama — no API key needed.

### 3 · Pull an LLM (Ollama)

```bash
ollama pull llama3.2          # recommended default  ~2 GB
# or
ollama pull phi4-mini         # faster               ~2.5 GB
# or
ollama pull mistral           # higher quality       ~4 GB
```

> If Ollama is already installed it auto-starts as a background service.
> Verify: `curl http://localhost:11434/v1/models`

### 4 · Start the backend

```bash
cd backend
pip install -r ../requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

✅ Swagger UI → http://localhost:8000/docs

### 5 · Start the frontend

```bash
# new terminal
cd frontend
npm install
npm run dev
```

✅ App → **http://localhost:5173**

---

## ⚙️ Configuration

All settings live in `.env` (copy from `.env.example`):

```env
# ── LLM provider ────────────────────────────────────────────────────────────
# Ollama (default — free, local)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
LLM_API_KEY=ollama

# OpenAI GPT-4o (better accuracy)
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o
# LLM_API_KEY=sk-...

# Groq (free tier, very fast)
# LLM_BASE_URL=https://api.groq.com/openai/v1
# LLM_MODEL=llama-3.3-70b-versatile
# LLM_API_KEY=gsk_...

# ── Data APIs (no key required) ──────────────────────────────────────────────
CBS_ODATA_BASE=https://opendata.cbs.nl/ODataFeed/odata
PDOK_OGC_BASE=https://api.pdok.nl/cbs/gebiedsindelingen/ogc/v1

# ── Cache TTLs ───────────────────────────────────────────────────────────────
CACHE_TTL_METADATA=3600    # 1 h  — CBS catalog
CACHE_TTL_GEOMETRY=86400   # 24 h — PDOK boundaries
CACHE_TTL_DATA=900         # 15 m — CBS observations

# ── Boundary year ────────────────────────────────────────────────────────────
DEFAULT_GEO_YEAR=2024
```

---

## 💬 Example Queries

```
# House values
Show average WOZ value by buurt in Utrecht
Gemiddelde woningwaarde per wijk in Amsterdam

# Population
Population density by gemeente in Noord-Holland
Bevolking per buurt in Rotterdam

# Income
Inkomen per inwoner per gemeente
Compare income across wijken in Den Haag

# Drill-down
Zoom into Amsterdam at wijk level
Show buurt level in Eindhoven

# Selection (click a polygon, then type)
What is the income here compared to the national average?
Show all buurten in this gemeente

# Conversational
What data can you show?
What is WOZ?
Help
```

---

## 🔌 API Reference

### `POST /chat`
Primary endpoint — natural language in, enriched GeoJSON out.

**Request**
```json
{
  "message": "Show average WOZ value by buurt in Utrecht",
  "history": []
}
```

**Response**
```json
{
  "message": "Gemiddelde WOZ-waarde per buurt in Utrecht. Bereik: 185 – 842 (96 buurten).",
  "plan": {
    "intent": "map_choropleth",
    "table_id": "86165NED",
    "measure_code": "GemiddeldeWOZWaardeVanWoningen_39",
    "geography_level": "buurt",
    "region_scope": "GM0344",
    "period": "2024JJ00",
    "classification": "quantile",
    "n_classes": 5,
    "message": "..."
  },
  "geojson": {
    "type": "FeatureCollection",
    "features": [...],
    "meta": {
      "measure_code": "GemiddeldeWOZWaardeVanWoningen_39",
      "period": "2024JJ00",
      "n_matched": 96,
      "value_min": 185.0,
      "value_max": 842.0,
      "breaks": [185, 290, 380, 490, 620, 842],
      "classification": "quantile"
    }
  },
  "warnings": []
}
```

### `GET /boundaries?level=buurt&scope=GM0344`
Fetch PDOK geometry without CBS data (for layer toggle, fast).

### `POST /map-data`
Execute a pre-built plan and return enriched GeoJSON.

### `POST /plan`
Generate a JSON plan from text without fetching any data.

### `GET /catalog`
List all indexed CBS geo-statistical tables.

### `GET /health`
Health check — returns `{"status": "ok"}`.

---

## 📁 Project Structure

```
CijfersChat/
│
├── backend/                         # Python / FastAPI
│   ├── app.py                       # Main application + endpoints
│   ├── config.py                    # Settings via pydantic-settings
│   ├── models.py                    # Pydantic request / response schemas
│   ├── cache.py                     # In-memory TTL caches
│   │
│   ├── catalog_index.py             # CBS catalog indexer — table / measure lookup
│   ├── cbs_client.py                # CBS OData v3 HTTP client + dimension detection
│   ├── spatial_service.py           # PDOK OGC API client + client-side filtering
│   ├── join_engine.py               # CBS DataFrame ⋈ PDOK GeoJSON + classification
│   ├── planner.py                   # LLM intent parser → JSON plan
│   │
│   └── tests/
│       ├── test_cbs_client.py       # CBS API integration tests
│       ├── test_join_engine.py      # Join + classification unit tests
│       └── test_planner.py         # Planner output validation
│
├── frontend/                        # React / TypeScript / Vite
│   └── src/
│       ├── App.tsx                  # Root component + layout
│       ├── main.tsx                 # React entry point
│       │
│       ├── api/
│       │   └── index.ts             # Typed backend client (fetch wrapper)
│       │
│       ├── store/
│       │   └── chatStore.ts         # Zustand global state
│       │
│       ├── types/
│       │   └── index.ts             # TypeScript interfaces
│       │
│       └── components/
│           ├── layout/
│           │   ├── AppShell.tsx     # Split-pane layout
│           │   └── ThemeToggle.tsx  # Dark / light mode
│           │
│           ├── chat/
│           │   ├── ChatPanel.tsx    # Scrollable message history
│           │   ├── MessageBubble.tsx# User / assistant bubbles
│           │   ├── PlanCard.tsx     # Collapsible JSON plan viewer
│           │   └── InputBar.tsx     # Chat input + send button
│           │
│           └── map/
│               ├── MapPanel.tsx     # MapLibre GL map + layers
│               ├── MapControls.tsx  # Layer toggle buttons
│               ├── MapLegend.tsx    # Choropleth legend
│               └── MapTooltip.tsx   # Hover tooltip
│
├── .env.example                     # Environment variable template
├── .gitignore
├── requirements.txt                 # Python dependencies
└── README.md
```

---

## 🔄 Data Flow

```
1. User types a message
       │
       ▼
2. POST /chat  { message, history }
       │
       ▼
3. planner.py  → LLM call → JSON Plan
   {
     table_id: "86165NED",
     measure_code: "GemiddeldeWOZWaardeVanWoningen_39",
     geography_level: "buurt",
     region_scope: "GM0344"
   }
       │
       ├──────────────────────────────┐
       ▼                              ▼
4. cbs_client.py                 spatial_service.py
   CBS OData v3 query            PDOK OGC API (paginated)
   $select + $filter             Full collection → client-side filter
   → pandas DataFrame            → GeoJSON FeatureCollection
       │                              │
       └──────────────┬───────────────┘
                       ▼
5. join_engine.py
   df.merge(geojson on statcode)
   Quantile / equal-interval classification
   → Enriched GeoJSON with "value", "class", "colour"
                       │
                       ▼
6. ChatResponse  { message, plan, geojson, warnings }
                       │
                       ▼
7. Frontend
   MapLibre renders choropleth
   Legend + tooltips
   Chat panel shows message + plan card
```

---

## 🧪 Running Tests

```bash
cd backend
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=. --cov-report=term-missing
```

| Test file | What it covers |
|-----------|---------------|
| `test_cbs_client.py` | CBS OData API connectivity + dimension detection |
| `test_join_engine.py` | CBS/PDOK join + quantile classification |
| `test_planner.py` | LLM plan output validation + JSON structure |

---

## 🛠️ Development

### Backend hot-reload
```bash
cd backend
uvicorn app:app --reload --port 8000
```

### Frontend hot-reload
```bash
cd frontend
npm run dev
```

### Lint
```bash
# Python
ruff check backend/
mypy backend/

# TypeScript
cd frontend && npm run lint
```

### Update PDOK boundaries
Boundaries are fetched live from PDOK on every cold-cache request. To force a refresh:
```bash
# Restart the backend — in-memory cache is cleared
uvicorn app:app --reload
```

Or change the target year:
```env
DEFAULT_GEO_YEAR=2025
```

---

## 🤖 LLM Design Principles

The LLM is intentionally **narrow-scoped**:

| LLM **does** | LLM **does not** |
|---|---|
| Parse natural language intent | Fetch data from CBS or PDOK |
| Output a structured JSON plan | Execute SQL or OData queries |
| Select the right table + measure | Render any UI |
| Translate to Dutch | Validate data quality |
| Handle conversation (greeting, help) | Make statistical judgements |

This means the system stays **deterministic and testable** — the same plan input always produces the same map, regardless of which LLM is used.

---

## 🔒 Privacy & Licensing

- **No user data is stored** — all queries are stateless
- **No API keys required** for CBS or PDOK
- CBS statistics and PDOK boundaries are published under **CC BY 4.0**
- This project is MIT licensed — attribution appreciated

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes
4. Push and open a Pull Request

Ideas welcome: new CBS tables, better classification methods, export to CSV/PNG, multilingual support.

---

## 📜 License

MIT © 2025 — see [LICENSE](LICENSE)

Data sources: [CBS StatLine](https://opendata.cbs.nl) · [PDOK](https://pdok.nl) — CC BY 4.0

---

<div align="center">

Built with ❤️ for open Dutch data

[CBS StatLine](https://opendata.cbs.nl) · [PDOK](https://pdok.nl) · [MapLibre GL](https://maplibre.org) · [FastAPI](https://fastapi.tiangolo.com)

</div>
