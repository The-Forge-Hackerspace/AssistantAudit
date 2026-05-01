/**
 * Smoke test du setup auth Playwright contre staging.
 * Vérifie que le storageState créé par global-setup permet d'accéder
 * à une page protégée sans redirection /login.
 */
import { test, expect } from '@playwright/test';

test('storageState donne accès au dashboard protégé', async ({ page }) => {
  const resp = await page.goto('/');
  expect(resp?.status(), 'GET /').toBeLessThan(400);
  // Si l'auth fonctionne on n'est PAS redirigé sur /login.
  await page.waitForLoadState('domcontentloaded');
  expect(page.url(), 'URL après chargement').not.toMatch(/\/login(\?|$)/);
});

test('API /api/v1/auth/me répond 200 avec le cookie', async ({ request }) => {
  const resp = await request.get('/api/v1/auth/me');
  expect(resp.status(), 'GET /auth/me').toBe(200);
  const body = await resp.json();
  expect(body.email).toBe(process.env.PLAYWRIGHT_ADMIN_EMAIL || 'admin@assistantaudit.fr');
});
