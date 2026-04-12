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

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![MapLibre GL](https://img.shields.io/badge/MapLibre_GL-4.x-396CB2?style=flat&logo=maplibre&logoColor=white)](https://maplibre.org)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1+-FFC300?style=flat)](https://duckdb.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![HF Spaces](https://img.shields.io/badge/🤗%20HF%20Spaces-Live%20Demo-orange)](https://huggingface.co/spaces/AthithyaLogan/CijfersChat)

> Type a plain-language question → get an interactive choropleth map of the Netherlands

**"Gasverbruik per gemeente in Noord-Holland"**
**"Aantal auto's per wijk in Utrecht"**
**"Inkomen per inwoner in Land van Cuijk"**

🚀 **[Live Demo on Hugging Face Spaces](https://huggingface.co/spaces/AthithyaLogan/CijfersChat)**

</div>

---

## ✨ Demo

https://github.com/user-attachments/assets/82ea5440-3d65-41a0-80b1-f55c292eb47d

---

## ✨ Features

| | |
|---|---|
| 🧠 **Two-LLM pipeline** | Planner (temp=0) → structured JSON plan · Narrator (temp=0.7) → conversational reply |
| 🗺️ **Live choropleth maps** | Gemeente · wijk · buurt level with smooth transitions and legend |
| 📊 **CBS StatLine** | Direct OData queries against official Dutch statistics |
| 🦆 **Local DuckDB pipeline** | Geometry + stats stored locally — no PDOK API calls at query time |
| 🏘️ **Wijk & buurt support** | Sub-municipality maps for whitelisted measures (vehicles, demographics, housing, WOZ) |
| 🏘️ **Spatial adjacency** | ST_Touches neighbor computation for buffer/compare queries |
| 🖱️ **Interactive selection** | Click any region → ask follow-up questions about it |
| 🌗 **Dark / light mode** | Fully themed UI |
| 🔌 **Any OpenAI-compatible LLM** | Groq (default, fast) · Ollama (free, local) · OpenAI · Azure OpenAI |
| 🐳 **Docker ready** | Single container — nginx + uvicorn, auto-bootstraps data on first run |
| 🤗 **HF Spaces hosted** | One-click deploy on Hugging Face Spaces |

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

### Option A — Hugging Face Spaces (no setup)

Visit **[https://huggingface.co/spaces/AthithyaLogan/CijfersChat](https://huggingface.co/spaces/AthithyaLogan/CijfersChat)** — no install required.

---

### Option B — Docker (self-hosted)

```bash
git clone https://github.com/athithyai/CijfersChat.git
cd CijfersChat

# Copy env and set your LLM provider (see Configuration below)
cp .env.example .env

# Build and run — data is auto-downloaded on first start (~3 min)
docker-compose up --build
```

App → **http://localhost:7860**

> Data is persisted in a Docker volume — subsequent starts are instant.

---

### Option C — Local development

#### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 20 LTS+ |
| Groq API key *(or Ollama for local LLM)* | — |

#### 1 · Clone & configure

```bash
git clone https://github.com/athithyai/CijfersChat.git
cd CijfersChat
cp .env.example .env   # edit LLM settings
```

#### 2 · Set your LLM (Groq recommended — free & fast)

Get a free API key at **[console.groq.com](https://console.groq.com)**, then in `.env`:

```env
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
LLM_API_KEY=gsk_...your_key...
```

Or use Ollama locally:

```bash
ollama pull llama3.2
```

```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
LLM_API_KEY=ollama
```

#### 3 · Download CBS data + geometry

```bash
cd backend
pip install -r ../requirements.txt
python download_data.py        # downloads CBS stats + gemeente geometry (~150 MB)
```

This creates:
- `data/cijfers.duckdb` — CBS statistics (long format)
- `data/cbs_spatial.duckdb` — CBS wide format + wijk/buurt + neighbors
- `data/gemeente_geo.duckdb` — gemeente polygons + ST_Touches neighbor pairs

#### 4 · Start backend

```bash
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
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

All settings in `.env` (copy from `.env.example`):

```env
# ── LLM provider ─────────────────────────────────────────────────────────────

# Groq (recommended — free tier, ~500 tok/s)
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant      # or llama-3.3-70b-versatile for better quality
LLM_API_KEY=gsk_...

# Ollama (free, local — no API key needed)
# LLM_BASE_URL=http://localhost:11434/v1
# LLM_MODEL=llama3.2
# LLM_API_KEY=ollama

# OpenAI (best accuracy)
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o
# LLM_API_KEY=sk-...

# ── Data APIs (public, no key required) ──────────────────────────────────────
CBS_ODATA_BASE=https://opendata.cbs.nl/ODataFeed/odata
PDOK_OGC_BASE=https://api.pdok.nl/cbs/gebiedsindelingen/ogc/v1
DEFAULT_GEO_YEAR=2024
```

---

## 💬 Example Queries

```
# Gemeente level
Gasverbruik per gemeente in Noord-Holland
Bevolkingsdichtheid per gemeente in Friesland
Gemiddelde WOZ-waarde per gemeente in Utrecht
Vergelijk Amsterdam met omliggende gemeenten

# Wijk & buurt level (whitelisted measures only)
Aantal auto's per wijk in Utrecht
Bevolking per buurt in Rotterdam
WOZ per wijk in Amsterdam
Personenauto's per buurt in Den Haag

# Conversational
Inkomen per inwoner in Land van Cuijk
Leg uit
Wat betekent dit?
Welke gemeente heeft het hoogste inkomen?
```

### Wijk/buurt whitelisted measures

Sub-municipality maps are available for:

| Category | Measures |
|----------|----------|
| Demographics | Inwoners, bevolkingsdichtheid, mannen/vrouwen, leeftijdsgroepen, huishoudens |
| Housing/WOZ | WOZ-waarde, woningvoorraad, koop/huurwoningen |
| Vehicles | Personenauto's totaal, auto's per huishouden |
| Business | Bedrijfsvestigingen |
| Area | Oppervlakte, omgevingsadressendichtheid |
| Education | Leerlingen PO, HBO, WO studenten |
| Care | Jeugdzorg, WMO-cliënten |

All other measures (energy, income, social benefits, proximity) are at gemeente level only.

---

## 🗂️ Data Sources

### CBS StatLine — Statistics

| Table ID | Description | Year |
|----------|-------------|------|
| `86165NED` | Kerncijfers wijken en buurten | 2025 |
| `85984NED` | Kerncijfers wijken en buurten | 2024 |
| `85618NED` | Kerncijfers wijken en buurten | 2023 |

Downloaded once locally via `download_data.py`. CBS OData API used as fallback when a measure is not in local DuckDB.

### PDOK — Boundaries

Gemeente/wijk/buurt polygon boundaries from the PDOK OGC API — cached locally on first run. All subsequent map requests read from disk/DuckDB, no live API calls needed.

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
│   ├── config.py               # Settings (pydantic-settings, reads .env)
│   └── data/
│       ├── cijfers.duckdb          # CBS statistics (long format)
│       ├── cbs_spatial.duckdb      # CBS wide format + regions + neighbors
│       ├── gemeente_geo.duckdb     # Gemeente polygons + ST_Touches adjacency
│       └── geometry/
│           ├── gemeente_raw.json   # PDOK gemeente geometry cache
│           ├── wijk_raw.json       # PDOK wijk geometry cache
│           └── buurt_raw.json      # PDOK buurt geometry cache
│
├── frontend/
│   └── src/
│       ├── api/client.ts       # Typed fetch wrapper
│       ├── store/chatStore.ts  # Zustand global state
│       ├── components/
│       │   ├── chat/           # ChatPanel, MessageBubble, InputBar, PlanCard
│       │   └── map/            # MapPanel, Legend, Tooltip, Controls
│       └── types/index.ts      # Shared TypeScript types
│
├── Dockerfile                  # Multi-stage: Node build + Python slim + nginx
├── docker-compose.yml          # Local Docker — port 7860, persistent data volume
├── nginx.conf                  # Proxy /api/ → uvicorn · serve SPA · port 7860
├── entrypoint.sh               # Auto-bootstrap CBS data on first container start
├── .env.example                # All config options documented
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

## 🐳 Docker

```bash
# Build and run
docker-compose up --build

# Force data refresh
docker-compose run --rm app python download_data.py

# Run without compose
docker build -t cijferschat .
docker run -p 7860:7860 --env-file .env cijferschat
```

App → **http://localhost:7860**

On first start, `entrypoint.sh` automatically downloads CBS statistics (~150 MB) and builds the geometry database. Subsequent starts use the persisted volume and are instant.

---

## 🤗 Hugging Face Spaces

The app is deployed at **[huggingface.co/spaces/AthithyaLogan/CijfersChat](https://huggingface.co/spaces/AthithyaLogan/CijfersChat)**.

To deploy your own Space:

```bash
# Add HF remote
git remote add hf https://huggingface.co/spaces/<your-username>/CijfersChat

# Push
git push hf master:main
```

Set these as **Space secrets** in Settings → Variables and secrets:

| Key | Value |
|-----|-------|
| `LLM_API_KEY` | `gsk_...` (Groq) |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | `llama-3.1-8b-instant` |

---

## 🧪 Tests

```bash
cd backend
pytest tests/ -v
```

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

[CBS StatLine](https://opendata.cbs.nl) · [PDOK](https://pdok.nl) · [MapLibre GL](https://maplibre.org) · [FastAPI](https://fastapi.tiangolo.com) · [DuckDB](https://duckdb.org) · [Groq](https://groq.com)

</div>
