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

// Routes publiques sur lesquelles on n'enclenche pas la cascade
// "401 → /auth/refresh → window.location='/login'". Sans ce garde-fou, un
// utilisateur qui arrive sur /login sans cookies provoque une boucle :
// /auth/me 401 → /auth/refresh 401 → reload sur /login → /auth/me 401 …
const PUBLIC_PATHS = ["/login", "/register"];

const isOnPublicPath = (): boolean => {
  if (typeof window === "undefined") return false;
  return PUBLIC_PATHS.includes(window.location.pathname);
};

const redirectToLogin = (): void => {
  if (typeof window === "undefined") return;
  if (isOnPublicPath()) return;
  window.location.href = "/login";
};

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
      // (sauf si on est déjà sur une route publique, sinon reload en boucle).
      if (originalRequest.url?.includes("/auth/refresh")) {
        redirectToLogin();
        return Promise.reject(error);
      }

      // Si la requête a échoué depuis une route publique, on ne tente même
      // pas le refresh : c'est un appel "best effort" (par ex. /auth/me au
      // mount de l'AuthContext) qu'il faut juste laisser remonter en 401.
      if (isOnPublicPath()) {
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
        redirectToLogin();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
