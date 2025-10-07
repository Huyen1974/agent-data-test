/**
 * E2E Test: Live Authentication and Knowledge Hub Data Load
 *
 * Purpose: "Bài test sống còn" - Xác minh rằng sau khi đăng nhập thực tế vào Google,
 * người dùng có thể thấy được dữ liệu tri thức từ Firestore.
 *
 * Scope: Test này chạy với production build và kết nối đến Firestore thực.
 *
 * Tuân thủ: APP-LAW §6.4 (CI Gates), HP-03 (No False Reporting)
 */

import { expect, test } from '@playwright/test';

// Skip test này trong môi trường local nếu không có credentials
test.skip(({ browserName }) => {
  return !process.env.GOOGLE_TEST_USER_EMAIL || !process.env.GOOGLE_TEST_USER_PASSWORD;
}, 'Skipping live auth test - credentials not available');

test.describe('Live Authentication and Knowledge Hub', () => {
  test('should authenticate with Google and load knowledge tree data', async ({ page, context }) => {
    // Bật console logging để debug
    page.on('console', (msg) => {
      console.log(`[browser:${msg.type()}]`, msg.text());
    });

    page.on('pageerror', (error) => {
      console.error('[pageerror]', error);
    });

    // BƯỚC 1: Truy cập trang chủ
    await page.goto('/', { waitUntil: 'networkidle' });

    // BƯỚC 2: Click nút "Đăng nhập bằng Google"
    const loginButton = page.locator('button:has-text("Đăng nhập bằng Google")');
    await expect(loginButton).toBeVisible({ timeout: 10000 });

    // BƯỚC 3: Thực hiện đăng nhập thực tế với Google
    // Khi click vào nút đăng nhập, một popup/redirect sẽ mở ra
    const [popup] = await Promise.all([
      context.waitForEvent('page'),
      loginButton.click()
    ]);

    // Chờ trang Google Sign-In load
    await popup.waitForLoadState('networkidle');

    // Điền email
    const emailInput = popup.locator('input[type="email"]');
    await emailInput.waitFor({ state: 'visible', timeout: 15000 });
    await emailInput.fill(process.env.GOOGLE_TEST_USER_EMAIL);
    await popup.locator('button:has-text("Next"), button:has-text("Tiếp theo")').click();

    // Chờ và điền password
    const passwordInput = popup.locator('input[type="password"]');
    await passwordInput.waitFor({ state: 'visible', timeout: 15000 });
    await passwordInput.fill(process.env.GOOGLE_TEST_USER_PASSWORD);
    await popup.locator('button:has-text("Next"), button:has-text("Tiếp theo")').click();

    // Chờ popup đóng (sign-in thành công)
    await popup.waitForEvent('close', { timeout: 30000 });

    // BƯỚC 4: Xác minh đăng nhập thành công trên trang chính
    // Kiểm tra hiển thị tên người dùng và nút đăng xuất
    await expect(page.locator('button:has-text("Đăng xuất")')).toBeVisible({ timeout: 15000 });

    // BƯỚC 5: XÁC MINH QUAN TRỌNG - Cây thư mục tri thức phải hiển thị
    // Đây là bước kiểm tra sống còn: dữ liệu từ Firestore phải load được

    // Chờ loading spinner biến mất (nếu có)
    await page.waitForFunction(() => {
      const loadingElement = document.querySelector('[role="progressbar"]');
      return !loadingElement || loadingElement.style.display === 'none';
    }, { timeout: 30000 });

    // Kiểm tra KHÔNG có thông báo lỗi "Không thể tải dữ liệu"
    const errorMessage = page.locator('text=/Không thể tải dữ liệu/i');
    await expect(errorMessage).not.toBeVisible({ timeout: 5000 });

    // Kiểm tra CÓ ít nhất 1 node trong cây tri thức
    // (Giả định rằng có ít nhất 1 document trong Firestore)
    const treeNodes = page.locator('[role="tree"] [role="treeitem"], .knowledge-node, .v-treeview-node');
    await expect(treeNodes.first()).toBeVisible({ timeout: 10000 });

    // Đếm số lượng nodes để đảm bảo có dữ liệu
    const nodeCount = await treeNodes.count();
    expect(nodeCount).toBeGreaterThan(0);

    console.log(`✓ Successfully loaded ${nodeCount} knowledge tree nodes`);

    // BƯỚC 6: Kiểm tra state của Firebase config (không được là fallback)
    const configCheck = await page.evaluate(() => {
      const config = window.__FIREBASE_CONFIG__;
      return {
        hasConfig: !!config,
        apiKey: config?.apiKey,
        projectId: config?.projectId,
        isFallback: config?.apiKey === 'AIzaSyDUMMY0000000000000000000000000000'
      };
    });

    expect(configCheck.hasConfig).toBe(true);
    expect(configCheck.isFallback).toBe(false);
    expect(configCheck.projectId).toBe('github-chatgpt-ggcloud');

    console.log('✓ Firebase config is correctly injected');
  });
});
