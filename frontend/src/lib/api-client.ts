import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

// ── Mutex pour le refresh concurrent ──
let isRefreshing = false;
let failedQueue: Array<{
  resolve: () => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ── Client Axios ──
// withCredentials: true → axios envoie automatiquement les cookies httpOnly
// d'authentification (aa_access_token, aa_refresh_token) sur chaque requête.
// JS ne lit jamais les tokens : ils sont posés et lus exclusivement par le backend.
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
  withCredentials: true,
});

// Intercepteur : gérer les 401 avec tentative de refresh token
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      // /auth/login : le 401 est attendu (mauvais identifiants), laisser l'UI le gérer
      if (originalRequest.url?.includes("/auth/login")) {
        return Promise.reject(error);
      }
      // Si c'est la route /auth/refresh qui a échoué → logout direct
      if (originalRequest.url?.includes("/auth/refresh")) {
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Mettre en file d'attente jusqu'à ce que le refresh soit terminé
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: () => resolve(api(originalRequest)),
            reject,
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { authApi } = await import("@/services/api");
        await authApi.refresh();
        processQueue(null);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
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

export default api;
