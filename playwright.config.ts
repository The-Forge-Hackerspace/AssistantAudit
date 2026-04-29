import { defineConfig, devices } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Charge .env.playwright (gitignored) si présent — credentials du serveur de test.
// On évite d'ajouter dotenv comme dep ; lecture manuelle suffit.
const envFile = path.join(__dirname, '.env.playwright');
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
}

const storageState = path.join(__dirname, 'playwright/.auth/state.json');
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const isHttps = baseURL.startsWith('https://');

// Si on cible un baseURL externe (staging, CI Docker, etc.), on n'essaie pas
// de relancer le frontend localement. PLAYWRIGHT_NO_WEBSERVER=1 force ce mode.
const noWebServer =
  !!process.env.CI ||
  !!process.env.PLAYWRIGHT_NO_WEBSERVER ||
  !baseURL.startsWith('http://localhost');

export default defineConfig({
  testDir: './tests',
  // En staging/HTTPS le backend rate-limite agressivement (auth: 5/min,
  // api: 30/min, par IP). Les workers parallèles partagent l'IP côté Caddy
  // donc on sérialise pour éviter les 429. En local on garde le parallèle.
  fullyParallel: !isHttps,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : isHttps ? 1 : 0,
  workers: process.env.CI ? 1 : isHttps ? 1 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],

  globalSetup: './tests/e2e/global-setup.ts',

  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    storageState,
    // tls internal de Caddy = CA auto-signée → on accepte les erreurs HTTPS.
    ignoreHTTPSErrors: isHttps,
  },

  webServer: noWebServer
    ? undefined
    : {
        command: 'npm --prefix frontend run dev -- --port 3000',
        url: 'http://localhost:3000',
        reuseExistingServer: true,
        timeout: 120_000,
      },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
