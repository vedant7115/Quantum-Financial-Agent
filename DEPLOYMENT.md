# 🚀 QUANTUM AGENT — Deployment Guide

This guide covers step-by-step instructions to deploy both the **FastAPI Backend** and the **React Vite Frontend** into production environments.

---

## 🏗️ Architecture Overview

| Component | Tech Stack | Recommended Hosting | Configuration Files |
| :--- | :--- | :--- | :--- |
| **Backend API** | Python 3.11 / FastAPI / Uvicorn | [Render](https://render.com) or [Railway](https://railway.app) | `backend/render.yaml`, `backend/Dockerfile`, `backend/Procfile` |
| **Frontend UI** | React 19 / Vite / TailwindCSS | [Vercel](https://vercel.com) or [Netlify](https://netlify.com) | `frontend/vercel.json`, `frontend/Dockerfile` |
| **Containerized** | Docker & Docker Compose | Self-Hosted / AWS / DigitalOcean | `docker-compose.yml` |

---

## 1. ⚡ Quick Deployment (Vercel + Render) [Recommended]

### Part A: Deploy the Backend to Render

1. Create a free account on [Render](https://render.com).
2. Click **New +** → **Web Service** → Connect your GitHub repository: `QUANTAM-AI-RESEARCH-AGENT`.
3. Configure the service settings:
   - **Name**: `quantum-agent-api`
   - **Root Directory**: `backend`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add **Environment Variables**:
   - `PYTHON_VERSION` = `3.11.0`
   - `GROQ_API_KEY` = `your_groq_api_key` *(from [console.groq.com](https://console.groq.com))*
   - `GROQ_MODEL` = `openai/gpt-oss-120b` *(or `llama-3.3-70b-versatile`)*
   - `ALLOWED_ORIGINS` = `*`
5. Click **Deploy Web Service**.
6. Once deployed, copy your Render backend URL (e.g., `https://quantum-agent-api.onrender.com`).

> **Render Blueprint Option**: You can also use Render's Blueprint feature. Render will automatically detect `render.yaml` and configure everything with one click.

---

### Part B: Deploy the Frontend to Vercel

1. Create a free account on [Vercel](https://vercel.com).
2. Click **Add New...** → **Project** → Import your GitHub repository.
3. In project configuration:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add **Environment Variable**:
   - `VITE_API_URL` = `https://quantum-agent-api.onrender.com/api` *(replace with your Render URL from Part A)*
5. Click **Deploy**.

Your fullstack application is now live on the internet! 🎉

---

## 2. 🐳 Deploy with Docker & Docker Compose

Deploy the full stack anywhere with Docker.

### Run Locally with Docker Compose:

1. Clone repository and create root `.env` from template:
   ```bash
   cp .env.example .env
   # Edit .env and enter your GROQ_API_KEY
   ```

2. Build and start containers:
   ```bash
   docker compose up --build -d
   ```

3. Access services:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

4. Stop containers:
   ```bash
   docker compose down
   ```

---

## 3. 🚂 Deploy to Railway

1. Sign in to [Railway](https://railway.app).
2. Click **New Project** → **Deploy from GitHub repo**.
3. Add backend service:
   - Root directory: `/backend`
   - Variables: `GROQ_API_KEY`, `ALLOWED_ORIGINS=*`
4. Add frontend service:
   - Root directory: `/frontend`
   - Variables: `VITE_API_URL=${{backend.RAILWAY_PUBLIC_DOMAIN}}/api`

---

## 4. 🔑 Environment Variables Reference

### Backend (`/backend/.env` or Render/Railway Settings)

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | Recommended | `""` | Enables multi-agent LLM reasoning. (System falls back to deterministic rule engines if absent). |
| `GROQ_MODEL` | Optional | `openai/gpt-oss-120b` | Model identifier used for Groq reasoning (`openai/gpt-oss-120b`, `llama-3.3-70b-versatile`, etc.). |
| `PORT` | Optional | `8000` | Port for the Uvicorn server to listen on. Render and Railway set this automatically. |
| `HOST` | Optional | `0.0.0.0` | Host IP address binding. |
| `ALLOWED_ORIGINS` | Optional | `*` | Comma-separated CORS allowed origins (e.g. `https://my-app.vercel.app,http://localhost:5173`). |
| `DEMO_MODE` | Optional | `false` | When set to `true`, serves pre-cached instant reports for AAPL, NVDA, TSLA, INFY, etc. |

### Frontend (`/frontend/.env` or Vercel/Netlify Settings)

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | Yes (in prod) | `http://localhost:8000/api` | The base URL of the deployed FastAPI backend endpoint. |

---

## 5. 🧪 Pre-Flight Verification Checklist

Before shipping to production, verify:
- [x] Backend dependencies in `backend/requirements.txt` (`fastapi`, `uvicorn[standard]`, `requests`, `yfinance`, `httpx`, `pandas`, `numpy`, `python-dotenv`)
- [x] Backend health endpoint `GET /health` and `GET /api/health`
- [x] Frontend builds cleanly: `npm --prefix frontend run build` (0 errors)
- [x] Frontend linter: `npm --prefix frontend run lint` (0 errors)
- [x] CORS middleware supports production and preview URLs
- [x] End-to-end integration test passes: `python backend/test_verification.py`
- [x] SPA rewrites configured for direct URLs in `frontend/vercel.json`
