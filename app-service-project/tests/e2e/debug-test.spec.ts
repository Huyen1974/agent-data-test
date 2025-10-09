import { expect, test } from '@playwright/test';

test('Debug: Check what the app actually renders', async ({ page }) => {
  // Set consistent viewport
  await page.setViewportSize({ width: 1280, height: 720 });

  console.log('Navigating to home page...');
  await page.goto('/', { waitUntil: 'networkidle' });

  console.log('Waiting for page to load...');
  await page.waitForTimeout(2000);

  // Get the page title and body text
  const title = await page.title();
  console.log('Page title:', title);

  const bodyText = await page.locator('body').textContent();
  console.log('Body text length:', bodyText?.length || 0);
  console.log('First 500 chars of body:', bodyText?.substring(0, 500) || 'No content');

  // Check for common elements
  const hasButton = await page.locator('button').count();
  console.log('Number of buttons found:', hasButton);

  const hasLoginButton = await page.locator('button:has-text("Đăng nhập")').count();
  console.log('Login buttons found:', hasLoginButton);

  // Check for Vue app root
  const vueRoot = await page.locator('#app').count();
  console.log('Vue app root (#app) found:', vueRoot);

  // Check for any error messages
  const errorElements = await page.locator('[class*="error"], [class*="Error"]').count();
  console.log('Error elements found:', errorElements);

  // Check console for errors
  const consoleMessages = [];
  page.on('console', msg => {
    console.log('CONSOLE:', msg.type(), msg.text());
    consoleMessages.push({ type: msg.type(), text: msg.text() });
  });

  // Check for JavaScript errors
  const errors = [];
  page.on('pageerror', err => {
    console.log('PAGE ERROR:', err.message);
    errors.push(err.message);
  });

  // Test if JavaScript is working
  const jsResult = await page.evaluate(() => {
    console.log('JavaScript is working!');
    return {
      hasWindow: typeof window !== 'undefined',
      hasDocument: typeof document !== 'undefined',
      hasFirebase: typeof window.__FIREBASE_CONFIG__ !== 'undefined',
      hasAuthAPI: typeof window.__AUTH_TEST_API__ !== 'undefined',
      userAgent: navigator.userAgent,
      url: window.location.href
    };
  });

  console.log('JavaScript execution result:', jsResult);

  await page.waitForTimeout(1000);

  console.log('Console messages captured:', consoleMessages.length);
  console.log('JavaScript errors:', errors.length);

  if (errors.length > 0) {
    console.log('Errors:', errors);
  }

  // Take screenshot for manual inspection
  await page.screenshot({ path: 'debug-screenshot.png', fullPage: true });

  // This test will always pass - it's just for debugging
  expect(true).toBe(true);
});