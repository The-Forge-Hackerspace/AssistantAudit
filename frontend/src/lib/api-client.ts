import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import Cookies from "js-cookie";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const TOKEN_KEY = "aa_access_token";
const REFRESH_KEY = "aa_refresh_token";
const TOKEN_EXPIRY_MINUTES = 15; // Doit correspondre au backend: JWT_ACCESS_TOKEN_EXPIRE_MINUTES

// ── Client Axios ──
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Intercepteur : ajouter le token JWT
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = Cookies.get(TOKEN_KEY);
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercepteur : gérer les 401
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Nettoyer les cookies JS
      Cookies.remove(TOKEN_KEY);
      Cookies.remove(REFRESH_KEY);
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Helpers Auth ──
export function setTokens(accessToken: string, refreshToken: string) {
  const isSecure = typeof window !== "undefined" && window.location.protocol === "https:";
  // Acc\u00e8s: expiry court align\u00e9 avec backend (15 min)
  // Note: js-cookie ne supporte pas httpOnly (restriction navigateur)
  // Les tokens rest JSON stockés en plain text mais avec sameSite=strict et secure pour CSRF
  Cookies.set(TOKEN_KEY, accessToken, { expires: TOKEN_EXPIRY_MINUTES / (24 * 60), sameSite: "strict", secure: isSecure });
  Cookies.set(REFRESH_KEY, refreshToken, { expires: 7, sameSite: "strict", secure: isSecure });
}

export function clearTokens() {
  Cookies.remove(TOKEN_KEY);
  Cookies.remove(REFRESH_KEY);
}

export function getAccessToken(): string | undefined {
  return Cookies.get(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!Cookies.get(TOKEN_KEY);
}

export default api;
