---
title: CijfersChat
emoji: 🗺️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">

<img src="https://cdn.cbs.nl/cdn/images/favicon.ico" width="80" height="80" alt="CBS" />

# CijfersChat

### Chat with Dutch regional statistics — on a live map

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![MapLibre GL](https://img.shields.io/badge/MapLibre_GL-4.x-396CB2?style=flat&logo=maplibre&logoColor=white)](https://maplibre.org)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1+-FFC300?style=flat)](https://duckdb.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)


> Type a plain-language question → get an interactive choropleth map of the Netherlands

**"Gasverbruik per gemeente in Noord-Holland"**
**"Bevolkingsdichtheid in Friesland"**
**"Inkomen per inwoner in Land van Cuijk"**

</div>

---

## ✨ Demo


https://github.com/user-attachments/assets/82ea5440-3d65-41a0-80b1-f55c292eb47d


---

## ✨ Features

| | |
|---|---|
| 🧠 **Two-LLM pipeline** | Planner (temp=0) → structured JSON plan · Narrator (temp=0.7) → conversational reply |
| 🗺️ **Live choropleth maps** | Gemeente level with smooth transitions and legend |
| 📊 **CBS StatLine** | Direct OData v3 queries against official Dutch statistics |
| 🦆 **Local DuckDB pipeline** | Geometry + stats stored locally — no PDOK API calls at query time |
| 🏘️ **Spatial adjacency** | ST_Touches neighbor computation for buffer/compare queries |
| 🖱️ **Interactive selection** | Click any municipality → ask follow-up questions about it |
| 🌗 **Dark / light mode** | Fully themed UI |
| 🔌 **Any OpenAI-compatible LLM** | Ollama (free, local) · OpenAI · Groq · Azure OpenAI |
| 🐳 **Docker ready** | Single container — nginx + uvicorn, auto-bootstraps data on first run |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          CijfersChat                              │
│                                                                    │
│  Frontend (React + Vite + MapLibre GL + Zustand)                  │
│    ChatPanel · MapPanel · Legend · Tooltip · InputBar             │
│                        │  POST /api/chat                          │
│  FastAPI Backend                                                   │
│    planner.py ──► LLM ──► JSON Plan                              │
│         │                   │                                      │
│         ▼                   ▼                                      │
│    cbs_client          spatial_service                             │
│    CBS OData v3    DuckDB-first (gemeente_geo.duckdb)             │
│    ↳ DuckDB fast   ↳ fallback: disk cache → PDOK API             │
│    path first                                                      │
│         │                   │                                      │
│         └─────── join_engine ──────► Enriched GeoJSON            │
│                                                                    │
│  Local data (backend/data/)                                        │
│    cijfers.duckdb       CBS statistics (long format)              │
│    cbs_spatial.duckdb   CBS wide format + regions + neighbors     │
│    gemeente_geo.duckdb  Gemeente polygons + ST_Touches adjacency  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option A — Docker (recommended)

```bash
git clone https://github.com/athithyai/CijfersChat.git
cd CijfersChat

# Copy env and set your LLM provider (see Configuration below)
cp .env.example .env

# Build and run — data is auto-downloaded on first start (~2 min)
docker-compose up --build
```

App → **http://localhost**

> Data is persisted in a Docker volume — subsequent starts are instant.

---

### Option B — Local development

#### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 20 LTS+ |
| Ollama *(for local LLM)* | latest |

#### 1 · Clone & configure

```bash
git clone https://github.com/athithyai/CijfersChat.git
cd CijfersChat
cp .env.example .env   # edit LLM settings if needed
```

#### 2 · Pull an LLM (Ollama)

```bash
ollama pull phi4          # recommended — best instruction following  ~9 GB
# or
ollama pull llama3.2      # smaller, faster                           ~2 GB
```

#### 3 · Download CBS data + geometry

```bash
cd backend
pip install -r ../requirements.txt
python download_data.py        # downloads stats CSVs + gemeente geometry
```

This creates:
- `data/cijfers.duckdb` — CBS statistics (long format)
- `data/gemeente_geo.duckdb` — gemeente polygons + ST_Touches neighbor pairs

> `gemeente_geo.duckdb` requires `gemeente_raw.json` to exist first.
> Start the backend once, let it warm up geometry from PDOK, then re-run.

#### 4 · Start backend

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

#### 5 · Start frontend

```bash
cd ../frontend
npm install
npm run dev
```

App → **http://localhost:5173**

---

## ⚙️ Configuration

All settings in `.env`:

```env
# ── LLM provider ─────────────────────────────────────────────────────────────
# Ollama (default — free, local)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=phi4
LLM_API_KEY=ollama

# OpenAI (better accuracy, ~$0.001/query with gpt-4o-mini)
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o-mini
# LLM_API_KEY=sk-...

# Groq (free tier, very fast)
# LLM_BASE_URL=https://api.groq.com/openai/v1
# LLM_MODEL=llama-3.3-70b-versatile
# LLM_API_KEY=gsk_...

# ── Data APIs ────────────────────────────────────────────────────────────────
CBS_ODATA_BASE=https://opendata.cbs.nl/ODataFeed/odata
PDOK_OGC_BASE=https://api.pdok.nl/cbs/gebiedsindelingen/ogc/v1

# ── Boundary year ─────────────────────────────────────────────────────────────
DEFAULT_GEO_YEAR=2024
```

---

## 💬 Example Queries

```
# Energy
Gasverbruik per gemeente in Noord-Holland
Elektriciteitsverbruik per gemeente

# Population
Bevolkingsdichtheid per gemeente in Friesland
Aantal inwoners per gemeente

# Income & housing
Inkomen per inwoner in Land van Cuijk
Gemiddelde WOZ-waarde per gemeente in Utrecht

# Compare
Vergelijk Amsterdam met omliggende gemeenten
Find me insights

# Conversational
Wat betekent dit?
Help
```

---

## 🗂️ Data Sources

### CBS StatLine — Statistics

| Table ID | Description | Year |
|----------|-------------|------|
| `86165NED` | Kerncijfers wijken en buurten | 2025 |
| `85984NED` | Kerncijfers wijken en buurten | 2024 |
| `85618NED` | Kerncijfers wijken en buurten | 2023 |

All tables are downloaded once locally via `download_data.py`. CBS OData API is used as a fallback when a measure is not in the local DuckDB.

### PDOK — Boundaries

Gemeente polygon boundaries are fetched from the PDOK OGC API on first run and cached locally in `gemeente_geo.duckdb`. All subsequent map requests read from DuckDB — no live API calls needed.

---

## 📁 Project Structure

```
CijfersChat/
│
├── backend/
│   ├── app.py                  # FastAPI endpoints
│   ├── planner.py              # Two-LLM pipeline (plan + narrate)
│   ├── cbs_client.py           # CBS OData client (DuckDB-first)
│   ├── spatial_service.py      # Geometry service (DuckDB-first → PDOK fallback)
│   ├── duckdb_client.py        # DuckDB query layer (cijfers + spatial + geometry)
│   ├── join_engine.py          # CBS data ⋈ geometry + classification
│   ├── ingest.py               # Full CBS + PDOK ingest pipeline
│   ├── download_data.py        # One-shot: download CBS CSVs + gemeente geometry
│   ├── models.py               # Pydantic schemas
│   ├── config.py               # Settings
│   └── data/
│       ├── cijfers.duckdb          # CBS statistics (long format)
│       ├── cbs_spatial.duckdb      # CBS wide format + regions + neighbors
│       ├── gemeente_geo.duckdb     # Gemeente polygons + ST_Touches adjacency
│       └── geometry/
│           └── gemeente_raw.json   # PDOK geometry disk cache
│
├── frontend/
│   └── src/
│       ├── api/client.ts       # Typed fetch wrapper
│       ├── store/chatStore.ts  # Zustand global state
│       ├── components/
│       │   ├── chat/           # ChatPanel, MessageBubble, InputBar, PlanCard
│       │   └── map/            # MapPanel, Legend, Tooltip, Controls
│       └── types/index.ts
│
├── Dockerfile                  # Multi-stage: Node build + Python slim + nginx
├── docker-compose.yml          # Local Docker with persistent data volume
├── nginx.conf                  # Proxy /api/ → uvicorn, serve SPA static files
├── entrypoint.sh               # Auto-bootstrap data on first container start
├── .env.example
└── requirements.txt
```

---

## 🔄 Data Flow

```
User message
    │
    ▼
POST /api/chat
    │
    ▼
planner.py → Planner LLM (temp=0) → JSON MapPlan
    { table_id, measure_code, geography_level, region_scope, province_scope }
    │
    ├─────────────────────────────────────┐
    ▼                                     ▼
cbs_client.py                     spatial_service.py
  1. DuckDB fast path               1. gemeente_geo.duckdb (local)
  2. CBS OData fallback             2. disk cache fallback
  → pandas DataFrame                3. PDOK API fallback
    │                                     │
    └──────────── join_engine ────────────┘
                       │
                       ▼
              Enriched GeoJSON + breaks + colours
                       │
    ┌──────────────────┤
    ▼                  ▼
Narrator LLM     ChatResponse
(temp=0.7)       { message, plan, geojson }
→ message text         │
                       ▼
                  MapLibre choropleth
```

---

## 🧪 Tests

```bash
cd backend
pytest tests/ -v
```

---

## 🐳 Docker

```bash
# Build
docker build -t cijferschat .

# Run (with persistent data volume)
docker-compose up

# Force data refresh
docker-compose run --rm app python download_data.py
```

On first start, `entrypoint.sh` automatically downloads CBS statistics (~150 MB) and builds the geometry database. Subsequent starts use the persisted volume and are instant.

---

## 🔒 Privacy & Licensing

- No user data is stored — all queries are stateless
- No API keys required for CBS or PDOK data
- CBS statistics and PDOK boundaries: **CC BY 4.0**
- This project: **MIT**

---

## 📜 License

MIT © 2025 — see [LICENSE](LICENSE)

Data: [CBS StatLine](https://opendata.cbs.nl) · [PDOK](https://pdok.nl) — CC BY 4.0

---

<div align="center">

Built for open Dutch data with ❤️

[CBS StatLine](https://opendata.cbs.nl) · [PDOK](https://pdok.nl) · [MapLibre GL](https://maplibre.org) · [FastAPI](https://fastapi.tiangolo.com) · [DuckDB](https://duckdb.org)

</div>
