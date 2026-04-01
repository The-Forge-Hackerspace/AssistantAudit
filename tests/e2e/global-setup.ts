/**
 * Playwright global setup — authenticates via API and saves storageState.
 * All browser tests reuse this state (cookies) so no UI login is needed.
 */
import { FullConfig, request } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const API_URL = process.env.PLAYWRIGHT_API_URL || 'http://127.0.0.1:8000';
const STORAGE_STATE_PATH = path.join(__dirname, '../../playwright/.auth/state.json');

async function globalSetup(config: FullConfig) {
  // Authenticate via backend API
  const context = await request.newContext({ baseURL: API_URL });

  const loginResp = await context.post('/api/v1/auth/login', {
    form: {
      username: 'admin@assistantaudit.local',
      password: 'Admin1234!',
    },
  });

  if (loginResp.status() !== 200) {
    const body = await loginResp.text();
    throw new Error(`Global setup: login failed (${loginResp.status()}): ${body}`);
  }

  const { access_token, refresh_token } = await loginResp.json();

  // Build storageState with cookies matching what the frontend expects
  const baseURL = config.projects[0]?.use?.baseURL || 'http://localhost:3000';
  const url = new URL(baseURL);

  const storageState = {
    cookies: [
      {
        name: 'aa_access_token',
        value: access_token,
        domain: url.hostname,
        path: '/',
        httpOnly: false,
        secure: url.protocol === 'https:',
        sameSite: 'Strict' as const,
        expires: -1, // session cookie
      },
      {
        name: 'aa_refresh_token',
        value: refresh_token,
        domain: url.hostname,
        path: '/',
        httpOnly: false,
        secure: url.protocol === 'https:',
        sameSite: 'Strict' as const,
        expires: -1,
      },
    ],
    origins: [],
  };

  // Ensure directory exists
  fs.mkdirSync(path.dirname(STORAGE_STATE_PATH), { recursive: true });
  fs.writeFileSync(STORAGE_STATE_PATH, JSON.stringify(storageState, null, 2));

  await context.dispose();
}

export default globalSetup;
