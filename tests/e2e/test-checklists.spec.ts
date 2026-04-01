/**
 * Tests E2E Sprint 2 — Checklists terrain
 * Prérequis: backend + frontend en cours d'exécution (docker compose up -d)
 * Frontend: http://localhost:3000 | Backend: http://localhost:8000
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';

test.describe('Checklists — mode terrain tablette', () => {
  test('Page login s\'affiche et frontend répond', async ({ page }) => {
    await page.goto(BASE_URL);
    // Le frontend redirige vers /login quand non authentifié
    await expect(page).toHaveURL(/login/, { timeout: 10000 });
    await expect(page.locator('h1, h2, form')).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: 'playwright-results/login-page.png', fullPage: true });
  });

  test('Page checklists est accessible après login', async ({ page }) => {
    // storageState handles auth — navigate directly
    await page.goto(`${BASE_URL}/audits/1/checklists`);

    // Prendre screenshot
    await page.screenshot({ path: 'playwright-results/checklists-page.png', fullPage: true });

    // Vérifier qu'il y a du contenu (templates ou message vide)
    const content = page.locator('main, .container, [class*="container"]').first();
    await expect(content).toBeVisible({ timeout: 5000 });
  });

  test('Viewport tablette (768x1024) — pas de scroll horizontal', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/login`);

    // Vérifier qu'il n'y a pas de scroll horizontal
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBeFalsy();

    await page.screenshot({ path: 'playwright-results/tablet-login.png', fullPage: true });
  });

  test('Viewport tablette (768x1024) — layout page checklists', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/audits/1/checklists`);

    // Même non authentifié, vérifier que le layout ne casse pas
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBeFalsy();

    await page.screenshot({ path: 'playwright-results/tablet-checklists.png', fullPage: true });
  });
});
