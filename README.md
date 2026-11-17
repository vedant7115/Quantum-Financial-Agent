# QUANTUM Financial Intelligence 🤖
## Institutional-Grade Multi-Agent Financial Research Platform

QUANTUM is an advanced, production-ready multi-agent investment research and decision-support system. It orchestrates parallel AI agent nodes to process real-time market data, financial statements, and news headlines, delivering a unified Market Bias synthesis report.

> **Version 2.0.0** rebuilds the research engine, the design and the plans. See [CHANGELOG.md](CHANGELOG.md) for everything that changed.

---

## 🚀 Architectural Capabilities

* **Real-Time Market Feeds**: Integrates `yfinance` to parse active market statistics and OHLCV price histories.
* **Exchange Suffix Auto-Resolution**: Detects common Indian stocks (e.g. `RELIANCE`, `TCS`, `INFY`) and auto-appends `.NS` for seamless Yahoo Finance querying, alongside standard US tickers (e.g., `AAPL`, `TSLA`).
* **Multi-Timeframe Audits**: Aggregates and evaluates technical variables across `15m`, `1h`, `4h`, `1d`, and `1w` price streams (resampling 1h data into 4h intervals via Pandas).
* **Dual-Mode Sentiment Agent**: Classifies media coverage via an offline keyword-matching lexicon with event triggers, or dynamically upgrades to a zero-shot LLM using **Google Gemini 1.5** when `GEMINI_API_KEY` is present.
* **Explainable Consensus Decisioning**: The Master Agent synthesizes results using a **40-35-25 weighted matrix**, outputting a unified non-advice **Market Bias** (`Bullish`, `Bearish`, `Neutral`), risk categories, and specific watchlist triggers.
* **Interactive Live Charts**: Embeds real-time **TradingView** candle widgets with interval selectors matching client preferences.
* **Visual Pipeline Timeline**: Illustrates step-by-step pipeline execution (`Market Data Ingest` ➔ `Technical Audits` ➔ `Fundamental Evaluations` ➔ `Sentiment Mapping` ➔ `Master Synthesis`) to track agent coordination in real-time.

---

## 📁 Repository Map

```
QUANTUM-AI-RESEARCH-AGENT/
│
├── backend/                    ← FastAPI Python Backend Gateway
│   ├── main.py                 ← Server entry point (cors & config loader)
│   ├── requirements.txt        ← Backend dependencies (yfinance, pandas, google-generativeai)
│   ├── render.yaml             ← Render infrastructure-as-code configuration
│   ├── agents/
│   │   ├── technical_agent.py  ← Volatility, support, resistance, and multi-timeframe checks
│   │   ├── fundamental_agent.py← Health, valuation, and compound growth scorers
│   │   ├── sentiment_agent.py  ← News lexicon scorer & zero-shot Gemini analyzer
│   │   └── master_agent.py     ← Weighted consensus matrix & narrative synthesizer
│   ├── services/
│   │   ├── stock_service.py    ← Real-time Yahoo Finance OHLCV & resampler
│   │   ├── news_service.py     ← Real-time news extractor and tagger
│   │   └── cache_service.py    ← In-memory thread-safe 5-min TTL cache
│   ├── models/
│   │   └── schemas.py          ← Pydantic v2 schemas and validation models
│   └── api/
│       └── routes.py           ← API endpoints, dotenv loader, and error handlers
│
├── frontend/                   ← React client application
│   ├── vercel.json             ← SPA routing configuration for Vercel
│   └── src/
│       ├── main.jsx            ← React renderer
│       ├── App.jsx             ← Dashboard state, timeline, and layout coordinator
│       ├── api.js              ← Axios client pointing to port 8000
│       ├── index.css           ← CSS theme tokens, glassmorphism, and animations
│       └── components/
│           ├── Header.jsx      ← Navbar switcher
│           ├── SearchBar.jsx   ← Quick-ticker bar
│           ├── KpiCards.jsx    ← Summarizes price, bias, confidence, and risk
│           ├── AgentCard.jsx   ← Multi-layout card displaying sub-agent details
│           ├── RecommendationCard.jsx ← Master Synthesis Report and agent weight charts
│           ├── StockInfoCard.jsx   ← Detailed company metrics
│           └── TradingViewChart.jsx ← Renders dynamic TradingView chart and selector
│
├── docs/                       ← Developer Architecture & Implementation Documentation
│   ├── architecture.md         ← Server-client topology and caching overview
│   ├── agent-flow.md           ← Sub-agent algorithms and weighting math
│   ├── api-design.md           ← Schema endpoints contracts
│   ├── security.md             ← Isolation controls, validation, and diagnostics
│   └── deployment.md           ← Step-by-step Vercel and Render configurations
│
├── .env.example                ← Environment template
└── README.md                   ← Master project guidebook
```

---

## 👥 Team Collaboration & Branch Ownership

To support parallel development during the Capgemini Buildathon, the repository uses a feature-branch model. The project is split into key areas with dedicated branch owners:

| Branch Name | Primary Owner | Module/Scope |
|:---|:---|:---|
| `frontend-ui` | **Abhinav** | React application, UI widgets, dashboards, visualizations |
| `backend-data` | **Priyansh** | FastAPI endpoints, stock services, database logic |
| `technical-agent` | **Ummehani** | Technical analysis agent modules, custom indicators |
| `fundamental-sentiment` | **Suhani** | Fundamental metrics and sentiment analysis agents |
| `architecture-docs` | **Vedant** | System diagrams, API specifications, markdown docs |

For detailed development guidelines, branching protocols, and merging instructions, see [CONTRIBUTING.md](file:///c:/Users/DELL/OneDrive/Desktop/Stock%20research%20Agent/CONTRIBUTING.md) and [TEAM_WORKFLOW.md](file:///c:/Users/DELL/OneDrive/Desktop/Stock%20research%20Agent/TEAM_WORKFLOW.md).

---

## ⚙️ How To Run Project

### 1. Environment Variables Configuration
Configure your environmental dependencies by creating a `.env` file in the **root** folder of the repository. (You can copy from `.env.example`).
```env
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: If you want to use the Groq fallback LLM (otherwise, the offline fallback heuristic engine handles analysis)
GROQ_API_KEY=your_groq_api_key_here
```

### 2. Backend Startup
The backend runs on **FastAPI (port 8000)**.
* **Option A: Quick Start script (Recommended on Windows)**:
  Simply double-click `start_backend.bat` from the root folder. This script will automatically verify your Python installation, auto-install requirements, and run the FastAPI server.
* **Option B: Manual Startup via terminal**:
  ```bash
  cd backend
  pip install -r requirements.txt
  python main.py
  ```
* **Verify Backend**:
  Open `http://localhost:8000/api/health` or view Swagger UI docs at `http://localhost:8000/docs`.

### 3. Frontend Startup
The frontend is a **React/Vite** client.
* **Option A: Quick Start script (Recommended on Windows)**:
  Double-click `start_frontend.bat` from the root folder. It will verify/install node dependencies and launch the dev server.
* **Option B: Manual Startup via terminal**:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```
* **Option C: Unified Startup via root scripts (Requires NPM)**:
  Since we've added root script proxying, you can run commands directly from the root workspace:
  ```bash
  # Install both frontend and backend dependencies
  npm run install-all
  
  # Start the React client (mapped to frontend/):
  npm run dev
  ```

### 4. Common Errors & Fixes

#### Error: `npm error enoent Could not read package.json`
* **Cause**: Running `npm run dev` or `npm install` inside the root workspace folder before we added root-level script maps.
* **Fix**: Ensure you either run commands in the `frontend` folder (`cd frontend`), use our pre-configured `start_frontend.bat` script, or run the proxies from root using `npm run dev`.

#### Error: `Fatal Python error: Failed to import encodings module` on Python 3.14
* **Cause**: On some systems, the default system Python (especially Python 3.14) has a corrupted library path or standard library package installation.
* **Fix**: Use our pre-configured `start_backend.bat` script, which automatically detects this error and falls back to a working Python 3.12 installation at `C:\Users\DELL\AppData\Local\Programs\Python\Python312\python.exe`. If running manually, launch with your explicit Python 3.12 executable path:
  ```bash
  "C:\Users\DELL\AppData\Local\Programs\Python\Python312\python.exe" main.py
  ```

#### Error: `CORS Blocked / Network Error` in Frontend UI
* **Cause**: The React server dynamically shifted to port `5174` or `5175` because port `5173` was already occupied, but the backend CORS configuration was restricted to `5173`.
* **Fix**: We updated `backend/main.py`'s CORS middleware to support fallback ports `5174`, `5175`, `5176`, and `3000` for both `localhost` and `127.0.0.1`. Make sure both servers are active.

---

## 📂 System Documentation

For detailed analysis of design decisions, review the following guides:
* [Architecture Design](file:///c:/Users/singh/QUANTAM-AI-RESEARCH-AGENT/docs/architecture.md)
* [Multi-Agent Consensus Flow](file:///c:/Users/singh/QUANTAM-AI-RESEARCH-AGENT/docs/agent-flow.md)
* [API Contract Design](file:///c:/Users/singh/QUANTAM-AI-RESEARCH-AGENT/docs/api-design.md)
* [Security & Safety Safeguards](file:///c:/Users/singh/QUANTAM-AI-RESEARCH-AGENT/docs/security.md)
* [Hosting & Deployment Guide](file:///c:/Users/singh/QUANTAM-AI-RESEARCH-AGENT/docs/deployment.md)

---

> ⚠️ **Disclaimer**: For educational purposes only. This platform represents quantitative analysis and does not provide financial or investment advice.
"# Quantum-AI-Research-Agent" 
