import re

from playwright.sync_api import Page, expect, sync_playwright

# Define absolute paths for screenshots
LOGGED_IN_SS_PATH = "/app/jules-scratch/verification/verification_loggedin.png"
GOODBYE_SS_PATH = "/app/jules-scratch/verification/verification_goodbye.png"
ERROR_SS_PATH = "/app/jules-scratch/verification/error_screenshot.png"


def run_verification(page: Page):
    """
    Verifies the user interface changes for login and logout.
    """
    # 1. Navigate to the app
    page.goto("http://localhost:5173/")

    # 2. Wait for the app and the test API to be ready
    expect(page.get_by_role("button", name="Đăng nhập bằng Google")).to_be_visible(
        timeout=10000
    )
    page.wait_for_function("window.__AUTH_TEST_API__", timeout=10000)

    # 3. Simulate user login using the test API
    page.evaluate(
        """
        window.__AUTH_TEST_API__.setUser({
            displayName: 'Jules Test',
            photoURL: 'https://i.pravatar.cc/150?u=jules_ux_fix_abs',
            email: 'jules.test@example.com',
        })
    """
    )

    # 4. Verify avatar and name are displayed
    avatar = page.locator(
        'div.v-avatar img[src="https://i.pravatar.cc/150?u=jules_ux_fix_abs"]'
    )
    expect(avatar).to_be_visible()
    expect(page.get_by_text("Jules Test")).to_be_visible()

    # 5. Take a screenshot of the logged-in state using an absolute path
    page.screenshot(path=LOGGED_IN_SS_PATH)

    # 6. Click the sign out button
    sign_out_button = page.get_by_role("button", name="Đăng xuất")
    sign_out_button.click()

    # 7. Verify redirection to the goodbye page
    expect(page).to_have_url(re.compile(r".*/goodbye"), timeout=5000)
    expect(page.get_by_text("Bạn đã đăng xuất thành công.")).to_be_visible()

    # 8. Take a screenshot of the goodbye page using an absolute path
    page.screenshot(path=GOODBYE_SS_PATH)


# --- Playwright Boilerplate ---
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            run_verification(page)
            print("Verification script completed successfully.")
        except Exception as e:
            print(f"An error occurred during verification: {e}")
            page.screenshot(path=ERROR_SS_PATH)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
