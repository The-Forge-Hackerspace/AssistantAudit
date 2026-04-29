/**
 * Spec agents : page UI + listing API.
 */
import { test, expect } from '@playwright/test';

test('UI : page agents charge avec header', async ({ page }) => {
  const resp = await page.goto('/agents');
  expect(resp?.status()).toBeLessThan(400);
  await expect(page.getByRole('heading', { name: /Agents/ })).toBeVisible({
    timeout: 10_000,
  });
});

test('API : GET /api/v1/agents répond une liste', async ({ request }) => {
  const r = await request.get('/api/v1/agents');
  expect(r.status()).toBe(200);
  const data = await r.json();
  // L'endpoint renvoie un tableau (vu lors du probe).
  expect(Array.isArray(data) || Array.isArray(data?.items)).toBe(true);
});
