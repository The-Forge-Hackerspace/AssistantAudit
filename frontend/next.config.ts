import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Use Linux-native path for build cache to avoid NTFS lockfile issues in WSL */
  distDir: process.env.NEXT_DIST_DIR || '.next',
};

export default nextConfig;
