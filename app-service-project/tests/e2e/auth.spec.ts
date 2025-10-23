import { test, expect } from '@playwright/test';

const LOGIN_BUTTON_LABEL = 'Đăng nhập bằng Google';
const LOGOUT_BUTTON_LABEL = 'Đăng xuất';

test.describe('Authentication smoke flow', () => {
  test('allows a user to sign in and sign out', async ({ page }) => {
    await page.goto('/');

    const loginButton = page.getByRole('button', { name: LOGIN_BUTTON_LABEL });
    await expect(loginButton).toBeVisible();

    await loginButton.click();

    const signOutButton = page.getByRole('button', { name: LOGOUT_BUTTON_LABEL });
    await expect(signOutButton).toBeVisible();

    await signOutButton.click();

    await expect(page.getByRole('button', { name: LOGIN_BUTTON_LABEL })).toBeVisible();
  });
});
