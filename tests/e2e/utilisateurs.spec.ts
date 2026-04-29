/**
 * Spec utilisateurs : page admin only + CRUD via API.
 */
import { test, expect } from '@playwright/test';
import { uniq } from './helpers';

test('UI : page utilisateurs charge pour admin', async ({ page }) => {
  const resp = await page.goto('/utilisateurs');
  expect(resp?.status()).toBeLessThan(400);
  await expect(
    page.getByRole('heading', { name: /Utilisateurs/ }),
  ).toBeVisible({ timeout: 10_000 });
});

test('API : créer / désactiver / supprimer un user auditeur', async ({ request }) => {
  const username = uniq('u').replace(/-/g, '').slice(0, 20);
  const email = `${username}@e2e.example.com`;
  const r = await request.post('/api/v1/users/', {
    data: {
      username,
      email,
      full_name: 'E2E User',
      role: 'auditeur',
      password: 'E2eUserPwd99!aa',
    },
  });
  expect(r.status(), await r.text()).toBe(201);
  const user = await r.json();
  try {
    const rUpd = await request.put(`/api/v1/users/${user.id}`, {
      data: { is_active: false },
    });
    expect(rUpd.status()).toBe(200);
    expect((await rUpd.json()).is_active).toBe(false);
  } finally {
    const rDel = await request.delete(`/api/v1/users/${user.id}`);
    expect([200, 204]).toContain(rDel.status());
  }
});

test('API : list users renvoie au moins l\'admin courant', async ({ request }) => {
  const r = await request.get('/api/v1/users/');
  expect(r.status()).toBe(200);
  const body = await r.json();
  const items = Array.isArray(body) ? body : body.items;
  expect(items.length).toBeGreaterThan(0);
});
