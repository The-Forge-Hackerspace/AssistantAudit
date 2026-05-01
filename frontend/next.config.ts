import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Use Linux-native path for build cache to avoid NTFS lockfile issues in WSL */
  distDir: process.env.NEXT_DIST_DIR || '.next',
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
      { source: '/api/:path*', destination: `${backendUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
