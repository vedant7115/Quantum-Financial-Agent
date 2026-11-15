// api.js — Axios API client
import axios from "axios";

// Normalize the backend base URL (handles with or without /api and trailing slashes)
const rawEnvUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000/api").trim();
const cleanUrl = rawEnvUrl.replace(/\/+$/, "");
export const BASE_URL = cleanUrl.endsWith("/api") ? cleanUrl : `${cleanUrl}/api`;
export const ROOT_URL = cleanUrl.replace(/\/api\/?$/, "");

// Optional payment link the upgrade buttons open (e.g. a Razorpay or Stripe link).
export const UPGRADE_URL = (import.meta.env.VITE_UPGRADE_URL || "").trim();

// ── Access key (paid plans) ──
// Stored on this device only and sent with every request as X-Quantum-Key.
const ACCESS_KEY_STORAGE = "quantum_access_key";

export function getAccessKey() {
  try {
    return localStorage.getItem(ACCESS_KEY_STORAGE) || "";
  } catch {
    return "";
  }
}

export function setAccessKey(key) {
  try {
    const clean = (key || "").trim();
    if (clean) localStorage.setItem(ACCESS_KEY_STORAGE, clean);
    else localStorage.removeItem(ACCESS_KEY_STORAGE);
  } catch {
    // Storage unavailable (private window); the key simply is not remembered.
  }
}

// Create an axios instance with default settings
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 45000, // Allow time for multi-agent synthesis
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const key = getAccessKey();
  if (key) config.headers["X-Quantum-Key"] = key;
  return config;
});

/** Plans and prices for the pricing page. */
export async function getPlans() {
  const response = await api.get("/plans");
  return response.data;
}

/** The caller's plan, locked sections and reports left today. */
export async function getUsage() {
  const response = await api.get("/usage");
  return response.data;
}

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
export async function checkBackendHealth(timeoutMs = 20000) {
  const healthUrl = `${ROOT_URL}/health`;
  const response = await axios.get(healthUrl, { timeout: timeoutMs });
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
