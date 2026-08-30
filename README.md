# Skylark Drones — Monday.com Business Intelligence Agent

An AI-powered, production-ready Business Intelligence Assistant built for **Skylark Drones**. The BI Agent enables founders and executives to query real-world messy operational and sales pipeline data across **Monday.com Boards** via a modern conversational interface.

---

## 🌟 Submission Overview & Mandatory Requirements

| Requirement | Status & Details |
| :--- | :--- |
| **1. GitHub Repository** | Source code structured in `/backend`, `/frontend`, and `/tools`. |
| **2. Hosted Application Link** | Deployment ready for Vercel/Render (see deployment section below). |
| **3. Detailed README & Decision Log** | Includes architecture, assumptions, trade-offs, AI tools used, and challenges faced (see [`DECISION_LOG.md`](file:///e:/skylark/DECISION_LOG.md)). |

---

## 🤖 AI Tools Used & Prototyping Approach

During the 5-hour assignment window, we utilized **Google DeepMind Antigravity AI Agent** for rapid pair-programming, architectural design, and automated data pipeline generation:
1. **Regex Data Pipeline Generation**: Generated regex extraction scripts to parse fragmented multi-page PDF columns into clean structured CSV datasets.
2. **Deterministic Architecture Design**: Co-designed the zero-hallucination architecture separating Pandas metric computation from natural language translation.
3. **Glassmorphism UI Development**: Iterated on modern React 18 + TailwindCSS components with live browser visual verification.

---

## 🚨 Key Challenges Faced & Solutions

1. **Fragmented PDF Multi-Page Tables**:
   - *Challenge*: Raw Deal Funnel & Work Order PDFs contained multi-page column groups where headers appeared on page 1 and data rows continued on page 5.
   - *Solution*: Developed a regex-based parser (`tools/generate_import_csvs.py`) to align deal values, sector categories, and status indicators reliably into 313 deal records and 163 work order records.

2. **Preventing LLM Calculation Hallucinations**:
   - *Challenge*: LLMs frequently miscalculate sums or mix up sector counts when analyzing large raw datasets.
   - *Solution*: Enforced **Strict Architecture Guardrails**: 100% of arithmetic is calculated deterministically using **Pandas**, passing pre-computed metric JSONs to the agent.

3. **Inconsistent Formats & `#VALUE!` Errors**:
   - *Challenge*: Input spreadsheets contained `#VALUE!` string errors, mixed currency text (`₹`, `Lakhs`, `Cr`), and inconsistent date formats.
   - *Solution*: Built a robust normalizer (`services/data_normalizer.py`) with fallback rules and explicit UI data quality context banners.

---

## 🏗️ Architecture Overview

```
skylark/
├── backend/
│   ├── main.py                  # FastAPI Application & REST Endpoints
│   ├── config.py                # Pydantic Settings & Environment Manager
│   ├── agent/
│   │   ├── agent.py             # BI Agent Pipeline & Fallback Summarizer
│   │   ├── query_router.py      # LLM Intent Router + Rule-Based Fallback
│   │   └── prompts.py           # System Prompts & Guardrails
│   ├── services/
│   │   ├── monday_service.py    # Monday.com GraphQL API Client
│   │   ├── data_normalizer.py   # Messy Data Normalization Logic
│   │   ├── analytics_service.py # Deterministic Metric Calculation Engine
│   │   └── data_quality_service.py # Data Quality Audit & Caveats Engine
│   └── models/
│       └── schemas.py           # Pydantic Request/Response Models
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Executive Glassmorphism UI
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx# Full-width Conversational Chat Container
│   │   │   ├── Message.jsx      # Markdown & HTML Table Renderer
│   │   │   └── InsightCard.jsx  # Structured Stat Badges
│   │   └── services/api.js      # Backend API Client
├── tools/
│   ├── generate_import_csvs.py  # Regex PDF Extractor & Monday.com CSV Generator
│   ├── deals_monday_import.csv  # Clean Deals Dataset (313 records)
│   └── work_orders_monday_import.csv # Clean Work Orders Dataset (163 records)
├── DECISION_LOG.md              # 2-Page Executive Decision Log
└── README.md                    # Setup & Submission Documentation
```

---

## 🛠️ Monday.com Board Setup Guide

### 1. Deals Board Configuration
Create a board named **`Deals`** in Monday.com with the following column types:

| Column Name | Recommended Monday.com Column Type | Description |
| :--- | :--- | :--- |
| `Deal Name` | Item Name (Text) | Primary Identifier |
| `Sector` | Dropdown / Status / Text | Industry Category |
| `Deal Stage` | Status | Pipeline stage (Prospecting, Proposal, Negotiation) |
| `Deal Value` | Numbers | Deal value in INR |
| `Close Date` | Date | Expected Close Date |
| `Status` | Status | Deal status (Won, Lost, Open) |

### 2. Work Order Tracker Board Configuration
Create a board named **`Work Order Tracker`** in Monday.com:

| Column Name | Recommended Monday.com Column Type | Description |
| :--- | :--- | :--- |
| `Order ID / Serial Number` | Item Name (Text) | Work Order Serial Number |
| `Customer Code` | Text | Client Identifier |
| `Sector` | Dropdown / Text | Sector/Industry |
| `Execution Status` | Status | Ongoing, Completed, Paused, Struck |
| `Planned Delivery Date` | Date | Baseline SLA Date |
| `Actual Delivery Date` | Date | Completion / Delivery Date |
| `Delay Reason` | Text | Operational bottleneck explanation |

### 3. Import Clean Data
Import `tools/deals_monday_import.csv` and `tools/work_orders_monday_import.csv` into your respective Monday.com boards.

---

## 🚀 Local Execution Guide

### Backend Setup (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend Setup (React / Vite)
```bash
cd frontend
npm install
npm run dev
```

Open your browser at **`http://127.0.0.1:5173/`**.

---

## 🌐 Public Deployment Guide (Render & Vercel)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Skylark BI Agent"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy Backend (Render.com / Railway)**:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Environment Variables: `MONDAY_API_TOKEN`, `DEALS_BOARD_ID`, `WORK_ORDERS_BOARD_ID`, `OPENAI_API_KEY`.

3. **Deploy Frontend (Vercel / Netlify)**:
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Environment Variable: `VITE_API_BASE_URL=<your-render-backend-url>`

---

## 📄 Submission Checklist
- [x] **Source Code**: Saved cleanly in repository
- [x] **Decision Log**: Saved in [`DECISION_LOG.md`](file:///e:/skylark/DECISION_LOG.md)
- [x] **README**: Updated with AI tools, challenges faced, architecture & deployment steps
