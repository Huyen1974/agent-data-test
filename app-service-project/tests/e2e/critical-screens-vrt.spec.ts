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

    // Wait for the knowledge tree to load (main workspace content)
    const knowledgeTree = page.locator('[data-testid="knowledge-tree"]');
    await expect(knowledgeTree).toBeVisible({ timeout: 10000 });

    // Wait for the navigation drawer (left sidebar) to be visible and stable
    const navigationDrawer = page.locator('.v-navigation-drawer').first();
    await expect(navigationDrawer).toBeVisible();

    // Allow extra time for any pending animations/transitions to complete
    await page.waitForTimeout(500);

    // Capture screenshot of the workspace layout showing the full interface
    // Note: This captures the unauthenticated view with login button visible
    await expect(page).toHaveScreenshot('workspace-layout.png', {
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
    });
  });
});
