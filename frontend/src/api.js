// api.js — Axios API client
import axios from "axios";

// Normalize the backend base URL (handles with or without /api and trailing slashes)
const rawEnvUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000/api").trim();
const cleanUrl = rawEnvUrl.replace(/\/+$/, "");
export const BASE_URL = cleanUrl.endsWith("/api") ? cleanUrl : `${cleanUrl}/api`;
export const ROOT_URL = cleanUrl.replace(/\/api\/?$/, "");

// Create an axios instance with default settings
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 45000, // Allow time for multi-agent synthesis
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Analyze a stock using all 4 agents.
 * Sends: { symbol: "AAPL" }
 */
export async function analyzeStock(symbol) {
  const response = await api.post("/analyze", { symbol });
  return response.data;
}

/**
 * Check if the backend server is running via API router.
 */
export async function checkHealth() {
  const response = await api.get("/health");
  return response.data;
}

/**
 * Perform a root health check (GET /health) to verify connectivity.
 */
export async function checkBackendHealth() {
  const healthUrl = `${ROOT_URL}/health`;
  const response = await axios.get(healthUrl, { timeout: 8000 });
  return response.data;
}

/**
 * Get raw stock data and chart data for a symbol.
 */
export async function getStockData(symbol) {
  const response = await api.get(`/stock/${symbol}`);
  return response.data;
}

export default api;
