/**
 * Spec sidebar-breakpoint : fige le contrat de la transition mobile/desktop
 * de la sidebar shadcn-ui après le bump du breakpoint de 768px à 1024px.
 *
 * Comportement attendu :
 *   < 1024px : sidebar = sheet (drawer mobile, fermé par défaut)
 *   ≥ 1024px : sidebar = panneau fixe 256px à gauche
 */
import { test, expect } from '@playwright/test';

test.describe('sidebar : transition au breakpoint 1024px', () => {
  test('1023px : la sidebar fixe est masquée (mode sheet)', async ({ page }) => {
    await page.setViewportSize({ width: 1023, height: 800 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Le conteneur fixe desktop n'est pas visible (classes lg:flex masquent < 1024).
    const fixedSidebar = page.locator('[data-slot="sidebar-container"]');
    await expect(fixedSidebar).toHaveCount(0);
  });

  test('1024px : la sidebar fixe est visible et fait ~256px de large', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 800 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const fixedSidebar = page.locator('[data-slot="sidebar-container"]').first();
    await expect(fixedSidebar).toBeVisible();
    const box = await fixedSidebar.boundingBox();
    expect(box, 'sidebar boundingBox').not.toBeNull();
    // La sidebar fait 256px (16rem) ; on tolère ±4px (padding inset).
    expect(box!.width).toBeGreaterThanOrEqual(252);
    expect(box!.width).toBeLessThanOrEqual(260);
  });

  test('800px (tablette) : trigger ouvre le sheet et la nav fonctionne', async ({ page }) => {
    await page.setViewportSize({ width: 800, height: 1000 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Sur tablette, la sidebar fixe est masquée. Le trigger ouvre le sheet.
    await page.getByRole('button', { name: /toggle sidebar/i }).click();

    // Le sheet contient le menu de navigation. Cliquer sur "Équipements"
    // navigue vers /equipements.
    const navLink = page.getByRole('link', { name: 'Équipements' }).first();
    await expect(navLink).toBeVisible({ timeout: 5_000 });
    await navLink.click();
    await page.waitForURL(/\/equipements/);
    expect(page.url()).toContain('/equipements');
  });

  test('1280px : navigation via la sidebar fixe', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Sidebar fixe visible, le lien "Entreprises" est cliquable directement.
    const navLink = page.getByRole('link', { name: 'Entreprises' }).first();
    await expect(navLink).toBeVisible();
    await navLink.click();
    await page.waitForURL(/\/entreprises/);
    expect(page.url()).toContain('/entreprises');
  });
});
