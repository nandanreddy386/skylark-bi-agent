# System Architecture Specification

## Architecture Overview

The Skylark BI Agent is a full-stack executive assistant designed to provide real-time, deterministic insights from Monday.com boards.

```
┌─────────────────────────────────────────────────────────┐
│                    React + Vite Frontend                │
│             (TailwindCSS v4 Executive UI)               │
└───────────────────────────┬─────────────────────────────┘
                            │ POST /api/chat
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
│                                                         │
│  1. Query Router (OpenAI JSON Mode Intent Detection)    │
│  2. Monday.com GraphQL Service (httpx + cursor paging)  │
│  3. Data Normalizer (Dirty record mapping & cleaning)   │
│  4. Deterministic Analytics Engine (Pandas processing)   │
│  5. Data Quality Service (Contextual warning tracking)   │
│  6. Business Explanation Engine (LLM Context Synthesis) │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
    ┌───────────────────┐       ┌───────────────────┐
    │  Monday.com API   │       │   OpenAI API      │
    │   (GraphQL v2)    │       │  (gpt-4o-mini)    │
    └───────────────────┘       └───────────────────┘
```

## Detailed Processing Flow

1. **User Question**: User asks a business question (e.g., *"What is our pipeline value for this quarter?"*).
2. **Intent Classification**: `QueryRouter` passes the text to `gpt-4o-mini` with strict JSON mode to identify intent (e.g. `pipeline_quarter`), sector filters, and time bounds.
3. **Dynamic Data Fetching**: `MondayService` queries the configured Monday.com board IDs using GraphQL with automatic cursor pagination.
4. **Data Normalization**: `data_normalizer.py` dynamically matches column names, converts dates to standard ISO, parses numeric values (removing currency markers), and standardizes sector names.
5. **Deterministic Calculation**: `analytics_service.py` runs Pandas aggregations. The LLM has zero involvement in calculations.
6. **Data Quality Tracking**: `data_quality_service.py` surfaces missing deal values or invalid entries that specifically affect the current query context.
7. **Executive Summary**: `agent.py` sends the pre-calculated numbers to `gpt-4o-mini` with strict system instructions prohibiting metric modification.
8. **UI Presentation**: React frontend displays structured markdown answers, metric cards, assumptions, and quality warnings.

## Key Components & File Map

* `backend/main.py`: REST API endpoints (`/api/chat`, `/health`, `/api/refresh`).
* `backend/config.py`: Environment variable configuration via Pydantic.
* `backend/services/monday_service.py`: GraphQL client for board schema inspection & cursor pagination.
* `backend/services/data_normalizer.py`: Data cleaning rules for messy tracker data.
* `backend/services/analytics_service.py`: Deterministic business intelligence math (Pandas).
* `backend/services/data_quality_service.py`: Context-aware quality issue tracking.
* `backend/agent/agent.py`: End-to-end pipeline orchestrator.
* `backend/agent/query_router.py`: LLM intent classifier.
* `backend/agent/prompts.py`: Constrained system prompts.
* `frontend/src/App.jsx`: Executive dashboard layout and sync controls.
* `frontend/src/components/ChatInterface.jsx`: Interactive message stream.
* `frontend/src/components/Message.jsx`: Markdown + Metric card bubble rendering.
