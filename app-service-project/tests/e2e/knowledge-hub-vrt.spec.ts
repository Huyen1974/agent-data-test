import { expect, test } from '@playwright/test';

test.describe('Knowledge Hub visual regression', () => {
  test('renders knowledge tree without regressions', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });

    await page.goto('/');

    // Wait for the navigation drawer and tree data to render.
    await expect(page.getByTestId('knowledge-tree')).toBeVisible();
    await expect(page.getByRole('option', { name: 'Dự án Incomex Corp' })).toBeVisible();

    // Allow any pending animations/transitions to complete before taking the snapshot.
    await page.waitForTimeout(250);

    const treeContainer = page.getByTestId('knowledge-tree');
    await expect(treeContainer).toHaveScreenshot({
      path: 'knowledge-hub-tree.png',
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
    });
  });
});
