/**
 * Spec responsive : pas de scroll horizontal sur des pages clés en
 * tablette (768x1024) et mobile (375x667).
 */
import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 667 },
];

const PATHS = ['/', '/equipements', '/outils/network-map'];

for (const vp of VIEWPORTS) {
  for (const path of PATHS) {
    test(`${vp.name} ${path} : pas de scroll horizontal`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      const resp = await page.goto(path);
      expect(resp?.status()).toBeLessThan(400);
      await page.waitForLoadState('networkidle');
      const overflow = await page.evaluate(() => {
        const html = document.documentElement;
        return html.scrollWidth - html.clientWidth;
      });
      // Tolérance : 1px (subpixel rounding sur certaines fontes).
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }
}
