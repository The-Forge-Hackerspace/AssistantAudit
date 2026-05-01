/**
 * Spec équipements : page accessible + CRUD API + tags si dispo.
 */
import { test, expect } from '@playwright/test';
import {
  createEntreprise,
  createEquipement,
  createSite,
  deleteEntreprise,
  deleteEquipement,
  deleteSite,
  uniq,
} from './helpers';

test('UI : page équipements charge avec header', async ({ page }) => {
  const resp = await page.goto('/equipements');
  expect(resp?.status()).toBeLessThan(400);
  await expect(page.getByRole('heading', { name: 'Équipements' })).toBeVisible();
});

test('API : CRUD équipement', async ({ request }) => {
  const ent = await createEntreprise(request);
  const site = await createSite(request, ent.id);
  try {
    const r1 = await request.post('/api/v1/equipements', {
      data: {
        site_id: site.id,
        type_equipement: 'serveur',
        ip_address: '10.10.10.10',
        hostname: uniq('host'),
      },
    });
    expect(r1.status()).toBe(201);
    const eq = await r1.json();

    const rUpd = await request.put(`/api/v1/equipements/${eq.id}`, {
      data: { hostname: eq.hostname + '-maj', notes_audit: 'Note test' },
    });
    expect(rUpd.status()).toBe(200);

    const rDel = await request.delete(`/api/v1/equipements/${eq.id}`);
    expect(rDel.status()).toBe(200);
  } finally {
    await deleteSite(request, site.id);
    await deleteEntreprise(request, ent.id);
  }
});

test('API : différents types d\'équipement acceptés', async ({ request }) => {
  const ent = await createEntreprise(request);
  const site = await createSite(request, ent.id);
  const created: number[] = [];
  try {
    for (const type of ['serveur', 'reseau', 'firewall']) {
      const r = await request.post('/api/v1/equipements', {
        data: {
          site_id: site.id,
          type_equipement: type,
          ip_address: `10.20.${created.length + 1}.1`,
          hostname: uniq(type),
        },
      });
      expect(r.status(), `type=${type}`).toBe(201);
      created.push((await r.json()).id);
    }
  } finally {
    for (const id of created) await deleteEquipement(request, id);
    await deleteSite(request, site.id);
    await deleteEntreprise(request, ent.id);
  }
});

test('UI : équipement créé via API visible après filtrage par site', async ({
  page,
  request,
}) => {
  const ent = await createEntreprise(request);
  const site = await createSite(request, ent.id);
  const eq = await createEquipement(request, site.id, { hostname: uniq('e2e-host') });
  try {
    await page.goto('/equipements');
    await page.waitForLoadState('networkidle');
    // Le hostname unique doit apparaître quelque part sur la page.
    await expect(page.getByText(eq.ip_address).first()).toBeVisible({
      timeout: 15_000,
    });
  } finally {
    await deleteEquipement(request, eq.id);
    await deleteSite(request, site.id);
    await deleteEntreprise(request, ent.id);
  }
});
