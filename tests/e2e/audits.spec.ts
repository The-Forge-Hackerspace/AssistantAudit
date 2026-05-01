/**
 * Spec audits : page list + CRUD API + accès aux endpoints synthèse / rapport.
 */
import { test, expect } from '@playwright/test';
import { createEntreprise, deleteEntreprise, uniq } from './helpers';

test('UI : page audits charge', async ({ page }) => {
  const resp = await page.goto('/audits');
  expect(resp?.status()).toBeLessThan(400);
  await expect(
    page.getByRole('heading', { name: /Projets d['’]audit|Audits/ }),
  ).toBeVisible({ timeout: 10_000 });
});

test('API : créer un audit puis le supprimer', async ({ request }) => {
  const ent = await createEntreprise(request);
  try {
    const r = await request.post('/api/v1/audits', {
      data: { nom_projet: uniq('CRUD-Audit'), entreprise_id: ent.id },
    });
    expect(r.status()).toBe(201);
    const audit = await r.json();
    expect(audit.entreprise_id).toBe(ent.id);

    const rGet = await request.get(`/api/v1/audits/${audit.id}`);
    expect(rGet.status()).toBe(200);
    const detail = await rGet.json();
    expect(detail.nom_projet).toBe(audit.nom_projet);

    const rDel = await request.delete(`/api/v1/audits/${audit.id}`);
    expect(rDel.status()).toBe(200);
  } finally {
    await deleteEntreprise(request, ent.id);
  }
});

test('API : update audit (status + objectifs)', async ({ request }) => {
  const ent = await createEntreprise(request);
  const r = await request.post('/api/v1/audits', {
    data: { nom_projet: uniq('U-Audit'), entreprise_id: ent.id },
  });
  const audit = await r.json();
  try {
    const rUpd = await request.put(`/api/v1/audits/${audit.id}`, {
      data: { status: 'EN_COURS', objectifs: 'Couvrir le périmètre AD' },
    });
    expect(rUpd.status()).toBe(200);
    const upd = await rUpd.json();
    expect(upd.status).toBe('EN_COURS');
  } finally {
    await request.delete(`/api/v1/audits/${audit.id}`);
    await deleteEntreprise(request, ent.id);
  }
});

test('API : exec summary endpoint répond pour audit existant', async ({ request }) => {
  const ent = await createEntreprise(request);
  const r = await request.post('/api/v1/audits', {
    data: { nom_projet: uniq('E-Audit'), entreprise_id: ent.id },
  });
  const audit = await r.json();
  try {
    const rSum = await request.get(`/api/v1/audits/${audit.id}/executive-summary`);
    // Soit 200 (synthèse vide générée), soit 404 (pas de checklists), soit 422.
    expect([200, 404, 422]).toContain(rSum.status());
  } finally {
    await request.delete(`/api/v1/audits/${audit.id}`);
    await deleteEntreprise(request, ent.id);
  }
});
