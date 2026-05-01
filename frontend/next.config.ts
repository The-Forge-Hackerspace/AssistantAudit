import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Use Linux-native path for build cache to avoid NTFS lockfile issues in WSL */
  distDir: process.env.NEXT_DIST_DIR || '.next',
  // Desactive le 308 redirect Next.js sur trailing slash : sans ce flag,
  // POST /api/v1/users/ -> 308 -> /api/v1/users -> rewrite vers backend:8000/api/v1/users
  // -> Starlette 307 -> backend:8000/api/v1/users/. Playwright suit ce redirect
  // cross-origin et perd les cookies httpOnly => 401. Avec skipTrailingSlashRedirect,
  // la rewrite matche directement la version slashee, pas de cascade de redirects.
  skipTrailingSlashRedirect: true,
  // Quand BACKEND_INTERNAL_URL est defini AU BUILD (ex. CI Docker, dev
  // compose), Next.js proxie /api/* vers le backend cote serveur. Permet au
  // front et aux tests Playwright d'utiliser des URLs relatives /api/v1/*
  // sans CORS ni reverse proxy externe. En prod (NPMPlus/Caddy en frontal),
  // on laisse vide : le reverse proxy externe assure le routage. Attention :
  // rewrites() est evaluee au BUILD, la valeur est figee dans l'image.
  async rewrites() {
    const backendUrl = process.env.BACKEND_INTERNAL_URL;
    if (!backendUrl) return [];
    return [
      // Pattern slashe en premier : preserve le trailing slash quand il est present.
      // Sans ca, ':path*' drop le slash et le backend renvoie un 307 absolute vers
      // backend:8000/...slashed, ce qui casse les cookies httpOnly cross-origin.
      { source: '/api/:path*/', destination: `${backendUrl}/api/:path*/` },
      { source: '/api/:path*', destination: `${backendUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
