import { expect, test } from '@playwright/test';

const TEST_USER = {
  displayName: 'Test User',
  email: 'test.user@example.com',
};

test('Google sign-in and sign-out UI flow', async ({ page, baseURL }) => {
  page.on('console', (msg) => {
    // eslint-disable-next-line no-console
    console.log(`[browser:${msg.type()}]`, msg.text());
  });
  page.on('pageerror', (error) => {
    // eslint-disable-next-line no-console
    console.log('[pageerror]', error);
  });

  await page.goto(baseURL ?? '/', { waitUntil: 'networkidle' });

  await page.waitForFunction(() => !!window.__AUTH_TEST_API__);

  await page.evaluate(() => {
    window.__AUTH_TEST_API__.setLoading(false);
    window.__AUTH_TEST_API__.setError('');
    window.__AUTH_TEST_API__.setUser(null);
  });

  const loginButton = page.locator('button:has-text("Đăng nhập bằng Google")');
  await expect(loginButton).toBeVisible();

  await page.evaluate((user) => {
    window.__AUTH_TEST_API__.setLoading(false);
    window.__AUTH_TEST_API__.setError('');
    window.__AUTH_TEST_API__.setUser(user);
  }, TEST_USER);

  await expect(page.locator('text=Test User')).toBeVisible();

  const logoutButton = page.locator('button:has-text("Đăng xuất")').first();
  await expect(logoutButton).toBeVisible();

  await logoutButton.click();

  // Wait for Vue to process the logout and update UI state
  await page.waitForTimeout(100);

  // Verify login button reappears after logout with increased timeout
  await expect(page.locator('button:has-text("Đăng nhập bằng Google")')).toBeVisible({
    timeout: 10000
  });
});
