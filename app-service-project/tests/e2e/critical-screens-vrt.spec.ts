import { expect, test } from '@playwright/test';

const TEST_USER = {
  displayName: 'Test User',
  email: 'test.user@example.com',
};

test.describe('Critical screens visual regression', () => {
  test('Login Page', async ({ page }) => {
    // Set consistent viewport
    await page.setViewportSize({ width: 1280, height: 720 });

    // Navigate to home page
    await page.goto('/');

    // Wait for the login button to appear
    const loginButton = page.locator('button:has-text("Đăng nhập bằng Google")');
    await expect(loginButton).toBeVisible();

    // Allow any pending animations to complete
    await page.waitForTimeout(250);

    // Capture screenshot of the login page
    await expect(page).toHaveScreenshot('login-page.png', {
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
    });
  });

  test('Workspace Layout', async ({ page, baseURL }) => {
    // Set consistent viewport
    await page.setViewportSize({ width: 1280, height: 720 });

    // Navigate to home page and wait for it to load completely
    await page.goto(baseURL ?? '/', { waitUntil: 'networkidle' });

    // Wait for the __AUTH_TEST_API__ to be available
    await page.waitForFunction(() => !!window.__AUTH_TEST_API__);

    // Initialize auth state and set logged-in user
    await page.evaluate(() => {
      window.__AUTH_TEST_API__.setLoading(false);
      window.__AUTH_TEST_API__.setError('');
      window.__AUTH_TEST_API__.setUser(null);
    });

    await page.evaluate((user) => {
      window.__AUTH_TEST_API__.setLoading(false);
      window.__AUTH_TEST_API__.setError('');
      window.__AUTH_TEST_API__.setUser(user);
    }, TEST_USER);

    // Wait for login to complete and user info to be visible in the app bar
    await expect(page.locator('text=Test User')).toBeVisible();

    // Wait for the logout button to confirm we're in logged-in state
    await expect(page.locator('button:has-text("Đăng xuất")')).toBeVisible();

    // Wait for the login button to disappear to ensure UI has fully transitioned
    await expect(page.locator('button:has-text("Đăng nhập bằng Google")')).not.toBeVisible();

    // Wait for the navigation drawer (left sidebar) to be visible and stable
    const navigationDrawer = page.locator('.v-navigation-drawer').first();
    await expect(navigationDrawer).toBeVisible();

    // Allow extra time for any pending animations/transitions to complete
    await page.waitForTimeout(500);

    // Capture screenshot of the workspace layout in logged-in state
    await expect(page).toHaveScreenshot('workspace-layout.png', {
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
    });
  });
});
