import { expect, Page } from '@playwright/test';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';

/**
 * Log in as admin via the UI login form.
 * Waits for a protected page to confirm auth succeeded.
 */
export async function loginAsAdmin(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/login`);
  const emailField = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]');
  await emailField.waitFor({ timeout: 5000 });
  await emailField.fill('admin@assistantaudit.local');
  await page.locator('input[type="password"]').fill('Admin1234!');
  await page.locator('button[type="submit"]').click();

  // Wait for auth to complete — don't rely on URL change event
  await page.waitForLoadState('networkidle', { timeout: 15000 });
  await page.goto(`${BASE_URL}/audits`);
  await expect(page).not.toHaveURL(/login/, { timeout: 10000 });
}
