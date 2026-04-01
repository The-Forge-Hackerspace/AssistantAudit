/**
 * Tests E2E Sprint 2 — Responsive / Tablette
 * Vérifie que le layout ne casse pas sur tablette 768x1024
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';

const PAGES_TO_TEST = [
  { path: '/', name: 'home' },
  { path: '/login', name: 'login' },
  { path: '/audits', name: 'audits' },
  { path: '/equipements', name: 'equipements' },
];

test.describe('Responsive — Tablette portrait 768x1024', () => {
  for (const { path, name } of PAGES_TO_TEST) {
    test(`${name} — pas de scroll horizontal`, async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}${path}`);
      await page.waitForLoadState('domcontentloaded');

      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });
      expect(hasHorizontalScroll).toBeFalsy();

      await page.screenshot({
        path: `playwright-results/tablet-${name}.png`,
        fullPage: true,
      });
    });
  }

  test('Checklists page — viewport tablette', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/audits/1/checklists`);
    await page.waitForLoadState('domcontentloaded');

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBeFalsy();

    await page.screenshot({
      path: 'playwright-results/tablet-checklists-detail.png',
      fullPage: true,
    });
  });

  test('Frontend charge correctement (titre AssistantAudit)', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page).toHaveTitle(/AssistantAudit/, { timeout: 10000 });
  });
});
