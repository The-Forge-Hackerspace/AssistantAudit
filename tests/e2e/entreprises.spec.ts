/**
 * Spec entreprises : liste UI + CRUD via API (cleanup auto).
 */
import { test, expect } from '@playwright/test';
import { createEntreprise, deleteEntreprise, uniq } from './helpers';

test('UI : page entreprises charge avec header et bouton Nouvelle', async ({ page }) => {
  const resp = await page.goto('/entreprises');
  expect(resp?.status()).toBeLessThan(400);
  await expect(page.getByRole('heading', { name: 'Entreprises' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Nouvelle entreprise/i })).toBeVisible();
});

test('UI : entreprise créée via API apparaît dans la liste', async ({ page, request }) => {
  const ent = await createEntreprise(request);
  try {
    await page.goto('/entreprises');
    // Désactive la pagination trop courte : recherche exact match
    const search = page.getByPlaceholder(/Rechercher/i);
    await search.fill(ent.nom);
    await expect(page.getByText(ent.nom).first()).toBeVisible({ timeout: 10_000 });
  } finally {
    await deleteEntreprise(request, ent.id);
  }
});

test('API : CRUD entreprise — create/get/update/delete', async ({ request }) => {
  const r1 = await request.post('/api/v1/entreprises', {
    data: { nom: uniq('CRUD-Ent'), secteur_activite: 'Test', contacts: [] },
  });
  expect(r1.status()).toBe(201);
  const ent = await r1.json();

  const rGet = await request.get(`/api/v1/entreprises/${ent.id}`);
  expect(rGet.status()).toBe(200);

  const rUpd = await request.put(`/api/v1/entreprises/${ent.id}`, {
    data: { nom: ent.nom + '-MAJ' },
  });
  expect(rUpd.status()).toBe(200);
  expect((await rUpd.json()).nom).toContain('-MAJ');

  const rDel = await request.delete(`/api/v1/entreprises/${ent.id}`);
  expect(rDel.status()).toBe(200);

  const rGone = await request.get(`/api/v1/entreprises/${ent.id}`);
  expect(rGone.status()).toBe(404);
});
