/**
 * Smoke tests publics : healthchecks et accessibilité de /login sans cookie.
 */
import { test, expect, request as pwRequest } from '@playwright/test';

test('GET /api/v1/health répond 200', async ({ request }) => {
  const r = await request.get('/api/v1/health');
  expect(r.status()).toBe(200);
  const body = await r.json();
  expect(body.status).toBe('healthy');
});

test('/login accessible sans cookies', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({
    baseURL,
    ignoreHTTPSErrors: true,
    storageState: { cookies: [], origins: [] },
  });
  const page = await ctx.newPage();
  const resp = await page.goto('/login');
  expect(resp?.status()).toBeLessThan(400);
  // L'AuthGuard affiche un spinner tant que /auth/me n'a pas répondu, et
  // l'intercepteur axios fait un round-trip /auth/refresh qui peut redéclencher
  // un reload via window.location.href quand il n'y a aucun cookie.
  // → on attend networkidle puis on cible l'input avec une timeout généreuse.
  await page.waitForLoadState('networkidle', { timeout: 20_000 });
  await expect(page.getByLabel('Identifiant')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('text=AssistantAudit').first()).toBeVisible();
  await ctx.close();
});

test('routes protégées redirigent /login sans cookies', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({
    baseURL,
    ignoreHTTPSErrors: true,
    storageState: { cookies: [], origins: [] },
  });
  const page = await ctx.newPage();
  await page.goto('/entreprises');
  await page.waitForURL(/\/login(\?|$)/, { timeout: 10_000 });
  expect(page.url()).toMatch(/\/login(\?|$)/);
  await ctx.close();
});

test('API /auth/me sans cookie répond 401', async ({ baseURL }) => {
  // Override storageState avec contexte vide.
  const ctx = await pwRequest.newContext({
    baseURL,
    ignoreHTTPSErrors: true,
    storageState: { cookies: [], origins: [] },
  });
  const r = await ctx.get('/api/v1/auth/me');
  expect(r.status()).toBe(401);
  await ctx.dispose();
});
