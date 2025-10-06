import { expect, test } from '@playwright/test';

const TEST_USER = {
  displayName: 'Test User',
  email: 'test.user@example.com',
};

test.describe('Critical screens visual regression', () => {
  test('Authentication Journey @smoke', async ({ page }) => {
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

  test('Authenticated Workspace Journey @smoke', async ({ page, baseURL }) => {
    // Set consistent viewport
    await page.setViewportSize({ width: 1280, height: 720 });

    // Navigate to home page and wait for it to load completely
    await page.goto(baseURL ?? '/', { waitUntil: 'networkidle' });

    // Wait for the initial page load - check for login button first
    await expect(page.locator('button:has-text("Đăng nhập bằng Google")')).toBeVisible();

    // Wait for the __AUTH_TEST_API__ to be available
    await page.waitForFunction(() => typeof window.__AUTH_TEST_API__ !== 'undefined');

    // Simulate authenticated user by setting the user state via the test API
    await page.evaluate((testUser) => {
      window.__AUTH_TEST_API__.setUser(testUser);
      window.__AUTH_TEST_API__.setLoading(false);
      window.__AUTH_TEST_API__.setError('');
    }, TEST_USER);

    // Give Vue a moment to process the reactive change
    await page.waitForTimeout(200);

    // CRITICAL: Wait for Vue to react and update the UI to show authenticated state
    // The logout button should now be visible
    await expect(page.locator('button:has-text("Đăng xuất")')).toBeVisible({ timeout: 5000 });

    // Verify the user's display name is shown
    await expect(page.locator('text=Test User')).toBeVisible();

    // Wait for the knowledge tree to load (main workspace content)
    const knowledgeTree = page.locator('[data-testid="knowledge-tree"]');
    await expect(knowledgeTree).toBeVisible({ timeout: 10000 });

    // Wait for the navigation drawer (left sidebar) to be visible and stable
    const navigationDrawer = page.locator('.v-navigation-drawer').first();
    await expect(navigationDrawer).toBeVisible();

    // Allow extra time for any pending animations/transitions to complete
    await page.waitForTimeout(500);

    // Capture screenshot of the workspace layout in authenticated state
    await expect(page).toHaveScreenshot('workspace-layout.png', {
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
    });
  });
});
