/**
 * Spec sites : page accessible + CRUD API (entreprise créée en setup).
 */
import { test, expect } from '@playwright/test';
import {
  createEntreprise,
  createSite,
  deleteEntreprise,
  deleteSite,
  uniq,
} from './helpers';

test('UI : page sites charge avec header et bouton Nouveau', async ({ page }) => {
  const resp = await page.goto('/sites');
  expect(resp?.status()).toBeLessThan(400);
  await expect(page.getByRole('heading', { name: 'Sites' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Nouveau site/i })).toBeVisible();
});

test('API : CRUD site sous une entreprise', async ({ request }) => {
  const ent = await createEntreprise(request);
  try {
    const r1 = await request.post('/api/v1/sites', {
      data: { nom: uniq('CRUD-Site'), entreprise_id: ent.id, adresse: '1 rue Test' },
    });
    expect(r1.status()).toBe(201);
    const site = await r1.json();
    expect(site.entreprise_id).toBe(ent.id);

    const rUpd = await request.put(`/api/v1/sites/${site.id}`, {
      data: { nom: site.nom + '-MAJ' },
    });
    expect(rUpd.status()).toBe(200);

    const rDel = await request.delete(`/api/v1/sites/${site.id}`);
    expect(rDel.status()).toBe(200);
  } finally {
    await deleteEntreprise(request, ent.id);
  }
});

test('UI : site créé via API visible dans la liste filtrée', async ({ page, request }) => {
  const ent = await createEntreprise(request);
  const site = await createSite(request, ent.id);
  try {
    await page.goto('/sites');
    const search = page.getByPlaceholder(/Rechercher/i);
    await search.fill(site.nom);
    await expect(page.getByText(site.nom).first()).toBeVisible({ timeout: 10_000 });
  } finally {
    await deleteSite(request, site.id);
    await deleteEntreprise(request, ent.id);
  }
});
