/**
 * Spec frameworks : page Référentiels + listing API (auto-syncés au boot).
 */
import { test, expect } from '@playwright/test';

test('UI : page Référentiels charge', async ({ page }) => {
  const resp = await page.goto('/frameworks');
  expect(resp?.status()).toBeLessThan(400);
  await expect(page.getByRole('heading', { name: 'Référentiels' })).toBeVisible({
    timeout: 10_000,
  });
});

test('API : GET /frameworks renvoie au moins un framework', async ({ request }) => {
  const r = await request.get('/api/v1/frameworks');
  expect(r.status()).toBe(200);
  const body = await r.json();
  const items = Array.isArray(body) ? body : body.items;
  expect(items.length).toBeGreaterThan(0);
  // Les frameworks auto-syncés depuis frameworks/*.yaml ont au moins ref_id + name.
  const sample = items[0];
  expect(sample).toHaveProperty('ref_id');
  expect(sample).toHaveProperty('name');
});
