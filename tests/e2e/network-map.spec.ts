/**
 * Spec network-map : couvre l'AC TOS-73.
 *
 * - structure UI (header, toolbar, 3 onglets)
 * - flows métier exécutés via l'API (la UI ReactFlow utilise drag/drop
 *   très instable à automatiser ; les endpoints REST sont la SSOT) :
 *     · ajout VLAN
 *     · édition VLAN
 *     · ajout connexion
 *     · suppression connexion
 * - export : marqué skip (export PNG/SVG ReactFlow → API Canvas non triviale
 *   à observer via download event ; nécessite double-clic sur bouton dynamique
 *   non labellé de manière stable). TODO: TOS-73 follow-up.
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

test('UI : page /outils/network-map charge avec header et toolbar', async ({ page }) => {
  const resp = await page.goto('/outils/network-map');
  expect(resp?.status()).toBeLessThan(400);
  await expect(
    page.getByText('Cartographie réseau', { exact: true }).first(),
  ).toBeVisible({ timeout: 15_000 });
});

test('UI : 3 onglets visibles (Topologie site / Vue multi-site / Vue détaillée)', async ({
  page,
}) => {
  await page.goto('/outils/network-map');
  await expect(page.getByRole('tab', { name: 'Topologie site' })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole('tab', { name: 'Vue multi-site' })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Vue détaillée' })).toBeVisible();
});

test('UI : navigation entre les 3 onglets fonctionne', async ({ page }) => {
  await page.goto('/outils/network-map');
  await page.getByRole('tab', { name: 'Vue multi-site' }).click();
  await expect(page.getByRole('tab', { name: 'Vue multi-site' })).toHaveAttribute(
    'aria-selected',
    'true',
  );
  await page.getByRole('tab', { name: 'Vue détaillée' }).click();
  await expect(page.getByRole('tab', { name: 'Vue détaillée' })).toHaveAttribute(
    'aria-selected',
    'true',
  );
});

test('UI : dark mode rend la page sans crash', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/outils/network-map');
  await expect(
    page.getByText('Cartographie réseau', { exact: true }).first(),
  ).toBeVisible({ timeout: 15_000 });
});

test('AC TOS-73 — ajout VLAN via API', async ({ request }) => {
  const ent = await createEntreprise(request);
  const site = await createSite(request, ent.id);
  try {
    const r = await request.post('/api/v1/network-map/vlans', {
      data: {
        site_id: site.id,
        vlan_id: 10,
        name: uniq('VLAN'),
        color: '#22aa55',
        description: 'VLAN E2E',
      },
    });
    expect(r.status()).toBe(201);
    const vlan = await r.json();
    expect(vlan.site_id).toBe(site.id);
    expect(vlan.vlan_id).toBe(10);

    // Visible dans la liste
    const rList = await request.get(
      `/api/v1/network-map/vlans?site_id=${site.id}`,
    );
    expect(rList.status()).toBe(200);
    const list = await rList.json();
    expect(list.find((v: { id: number }) => v.id === vlan.id)).toBeTruthy();
  } finally {
    await deleteSite(request, site.id);
    await deleteEntreprise(request, ent.id);
  }
});

test('AC TOS-73 — édition VLAN via API', async ({ request }) => {
  const ent = await createEntreprise(request);
  const site = await createSite(request, ent.id);
  try {
    const create = await request.post('/api/v1/network-map/vlans', {
      data: { site_id: site.id, vlan_id: 20, name: 'V20', color: '#aa2255' },
    });
    const vlan = await create.json();
    const upd = await request.put(`/api/v1/network-map/vlans/${vlan.id}`, {
      data: { name: 'V20-updated', color: '#0044ff' },
    });
    expect(upd.status()).toBe(200);
    const updated = await upd.json();
    expect(updated.name).toBe('V20-updated');
    expect(updated.color.toLowerCase()).toBe('#0044ff');
  } finally {
    await deleteSite(request, site.id);
    await deleteEntreprise(request, ent.id);
  }
});

test('AC TOS-73 — ajout puis suppression d\'une connexion réseau (link)', async ({
  request,
}) => {
  const ent = await createEntreprise(request);
  const site = await createSite(request, ent.id);
  const eq1 = await createEquipement(request, site.id, { ip_address: '10.50.1.1' });
  const eq2 = await createEquipement(request, site.id, { ip_address: '10.50.1.2' });
  try {
    const create = await request.post('/api/v1/network-map/links', {
      data: {
        site_id: site.id,
        source_equipement_id: eq1.id,
        target_equipement_id: eq2.id,
        link_type: 'ethernet',
        bandwidth: '1G',
      },
    });
    expect(create.status()).toBe(201);
    const link = await create.json();
    expect(link.source_equipement_id).toBe(eq1.id);
    expect(link.target_equipement_id).toBe(eq2.id);

    // suppression
    const del = await request.delete(`/api/v1/network-map/links/${link.id}`);
    expect(del.status()).toBe(200);

    // confirmé absent
    const gone = await request.get(`/api/v1/network-map/links/${link.id}`);
    expect(gone.status()).toBe(404);
  } finally {
    await deleteEquipement(request, eq1.id);
    await deleteEquipement(request, eq2.id);
    await deleteSite(request, site.id);
    await deleteEntreprise(request, ent.id);
  }
});

test('AC TOS-73 — site map endpoint renvoie nodes + edges', async ({ request }) => {
  const ent = await createEntreprise(request);
  const site = await createSite(request, ent.id);
  const eq1 = await createEquipement(request, site.id, { ip_address: '10.51.1.1' });
  const eq2 = await createEquipement(request, site.id, { ip_address: '10.51.1.2' });
  try {
    await request.post('/api/v1/network-map/links', {
      data: {
        site_id: site.id,
        source_equipement_id: eq1.id,
        target_equipement_id: eq2.id,
      },
    });
    const r = await request.get(`/api/v1/network-map/site/${site.id}`);
    expect(r.status()).toBe(200);
    const map = await r.json();
    expect(map.site_id).toBe(site.id);
    expect(map.nodes.length).toBe(2);
    expect(map.edges.length).toBe(1);
  } finally {
    await deleteEquipement(request, eq1.id);
    await deleteEquipement(request, eq2.id);
    await deleteSite(request, site.id);
    await deleteEntreprise(request, ent.id);
  }
});

test.skip('UI : export PNG/SVG déclenche un download', async () => {
  // TODO TOS-73 : automatiser quand le bouton "Exporter" sera labellé
  // de manière stable et que l'export sera un véritable download (pas un
  // canvas data-url consommé en mémoire). Voir composants Toolbar.tsx.
});
