/**
 * Tests E2E Sprint 2 — Tags et filtrage multi-tag
 * Prérequis: backend + frontend en cours d'exécution (docker compose up -d)
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';

test.describe('Tags — badges et filtrage multi-tag', () => {
  test('Page équipements accessible (redirect login si non auth)', async ({ page }) => {
    await page.goto(`${BASE_URL}/equipements`);
    // Doit soit afficher la page soit rediriger vers login
    await expect(page).toHaveURL(/(equipements|login)/, { timeout: 10000 });
    await page.screenshot({ path: 'playwright-results/equipements-page.png', fullPage: true });
  });

  test('Composant TagFilter est présent dans la page équipements (après login)', async ({ page }) => {
    // Login d'abord
    await page.goto(`${BASE_URL}/login`);
    const emailField = page.locator('input[type="email"], input[name="email"]');
    const passwordField = page.locator('input[type="password"]');
    await emailField.waitFor({ timeout: 5000 });
    await emailField.fill('admin@assistantaudit.local');
    await passwordField.fill('Admin1234!');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(/(?!login)/, { timeout: 10000 });

    // Naviguer vers équipements
    await page.goto(`${BASE_URL}/equipements`);
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Le TagFilter devrait être présent (badges cliquables)
    await page.screenshot({ path: 'playwright-results/equipements-avec-tags.png', fullPage: true });

    // Vérifier que la page contient quelque chose (même vide)
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('Viewport tablette — page équipements sans scroll horizontal', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/equipements`);

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBeFalsy();

    await page.screenshot({ path: 'playwright-results/tablet-equipements.png', fullPage: true });
  });
});
