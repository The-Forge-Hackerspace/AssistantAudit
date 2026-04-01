import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import Cookies from "js-cookie";

// ── Mutex pour le refresh concurrent ──
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
};

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

// Intercepteur : gérer les 401 avec tentative de refresh token
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      // Si c'est la route /auth/refresh qui a échoué → logout direct
      if (originalRequest.url?.includes("/auth/refresh")) {
        clearTokens();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Mettre en file d'attente jusqu'à ce que le refresh soit terminé
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers["Authorization"] = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { authApi } = await import("@/services/api");
        const tokens = await authApi.refresh();
        processQueue(null, tokens.access_token);
        originalRequest.headers["Authorization"] = `Bearer ${tokens.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        clearTokens();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
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
