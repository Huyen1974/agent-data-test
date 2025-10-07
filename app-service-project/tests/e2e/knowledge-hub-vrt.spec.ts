import { expect, test } from '@playwright/test';

test.describe('Knowledge Hub visual regression', () => {
  test('Knowledge Hub Display Journey @smoke', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });

    await page.goto('/', { waitUntil: 'networkidle' });

    // Wait for the navigation drawer and tree data to render with explicit timeout
    await expect(page.getByTestId('knowledge-tree')).toBeVisible({ timeout: 10000 });

    // Wait for the first tree item to ensure data is loaded
    await expect(page.getByRole('option', { name: 'Dự án Incomex Corp' })).toBeVisible({
      timeout: 5000
    });

    // Allow animations/transitions to complete before snapshot
    await page.waitForTimeout(500);

    const treeContainer = page.getByTestId('knowledge-tree');
    await expect(treeContainer).toHaveScreenshot({
      path: 'knowledge-hub-tree.png',
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
      timeout: 10000
    });
  });
});
