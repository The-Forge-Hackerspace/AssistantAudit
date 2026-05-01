/**
 * Playwright global setup — authentifie via API et persiste le storageState
 * en réutilisant les cookies httpOnly réellement émis par le backend.
 *
 * Variables d'env reconnues (chargées par playwright.config.ts depuis .env.playwright) :
 *   PLAYWRIGHT_BASE_URL          URL du frontend — fallback http://localhost:3000
 *   PLAYWRIGHT_API_URL           URL backend — par défaut, dérivée du baseURL
 *                                (Caddy proxie /api/* sur le même hôte)
 *   PLAYWRIGHT_ADMIN_EMAIL       Email admin — fallback admin@assistantaudit.fr
 *   PLAYWRIGHT_ADMIN_PASSWORD    Password admin — fallback Admin1234!
 */
import { FullConfig, request } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const STORAGE_STATE_PATH = path.join(__dirname, '../../playwright/.auth/state.json');

// Durée de fraîcheur du storageState mis en cache (par défaut 10 min). En staging
// le rate-limiter sur /auth/login est strict (5 tentatives/min, blocage 5 min) :
// on évite de relogger à chaque run pour ne pas le déclencher.
const STORAGE_TTL_MS = Number(process.env.PLAYWRIGHT_STORAGE_TTL_MS || 10 * 60 * 1000);

async function loginWithRetry(
  context: import('@playwright/test').APIRequestContext,
  email: string,
  password: string,
): Promise<import('@playwright/test').APIResponse> {
  let lastResp: import('@playwright/test').APIResponse | null = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const resp = await context.post('/api/v1/auth/login', {
      form: { username: email, password },
    });
    if (resp.status() === 200) return resp;
    lastResp = resp;
    if (resp.status() !== 429) break;
    const retryAfter = Number(resp.headers()['retry-after'] || 60);
    const waitMs = Math.min(retryAfter, 60) * 1000 + 1000;
    // eslint-disable-next-line no-console
    console.log(`[global-setup] login 429 ; attente ${waitMs / 1000}s avant retry…`);
    await new Promise((r) => setTimeout(r, waitMs));
  }
  return lastResp!;
}

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL || 'http://localhost:3000';
  const apiURL = process.env.PLAYWRIGHT_API_URL || baseURL;
  const adminEmail = process.env.PLAYWRIGHT_ADMIN_EMAIL || 'admin@assistantaudit.fr';
  const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD || 'Admin1234!';

  // Réutilise un storageState récent pour éviter de spammer /auth/login.
  if (!process.env.PLAYWRIGHT_FORCE_LOGIN && fs.existsSync(STORAGE_STATE_PATH)) {
    const age = Date.now() - fs.statSync(STORAGE_STATE_PATH).mtimeMs;
    if (age < STORAGE_TTL_MS) {
      // Vérifie rapidement que le cookie est encore accepté.
      const probe = await request.newContext({
        baseURL: apiURL,
        ignoreHTTPSErrors: apiURL.startsWith('https://'),
        storageState: STORAGE_STATE_PATH,
      });
      const me = await probe.get('/api/v1/auth/me');
      await probe.dispose();
      if (me.status() === 200) {
        // eslint-disable-next-line no-console
        console.log(
          `[global-setup] storageState frais (${Math.round(age / 1000)}s) — login skip.`,
        );
        return;
      }
    }
  }

  const context = await request.newContext({
    baseURL: apiURL,
    ignoreHTTPSErrors: apiURL.startsWith('https://'),
  });

  const loginResp = await loginWithRetry(context, adminEmail, adminPassword);

  if (loginResp.status() !== 200) {
    const body = await loginResp.text();
    throw new Error(
      `Global setup: login failed (${loginResp.status()}) ` +
        `against ${apiURL} as ${adminEmail}: ${body}`,
    );
  }

  // Le backend pose des cookies httpOnly via Set-Cookie. On laisse Playwright
  // les capter (storageState() inclut tous les cookies du context).
  const apiState = await context.storageState();
  await context.dispose();

  // Le storageState API ne suffit pas si l'hôte du frontend diffère de l'API
  // (cas mono-domaine via Caddy : ça matche). Sinon on duplique les cookies
  // sur le hostname du frontend.
  const apiHost = new URL(apiURL).hostname;
  const frontendHost = new URL(baseURL).hostname;
  const dupedCookies = apiState.cookies.flatMap((c) =>
    c.domain.replace(/^\./, '') === apiHost && apiHost !== frontendHost
      ? [c, { ...c, domain: frontendHost }]
      : [c],
  );

  const storageState = { ...apiState, cookies: dupedCookies };

  fs.mkdirSync(path.dirname(STORAGE_STATE_PATH), { recursive: true });
  fs.writeFileSync(STORAGE_STATE_PATH, JSON.stringify(storageState, null, 2));
}

export default globalSetup;
