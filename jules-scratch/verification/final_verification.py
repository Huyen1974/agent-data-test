from playwright.sync_api import expect, sync_playwright


def run_final_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Go to the local development server URL
            page.goto("http://localhost:5173/", timeout=15000)

            # Wait for the main layout and auth controls to be ready
            login_button = page.get_by_role("button", name="Đăng nhập bằng Google")
            expect(login_button).to_be_visible(timeout=10000)

            # Wait for the expected error message due to Firestore timeout
            error_message = page.get_by_text("Lỗi kết nối tới kho tri thức.")
            expect(error_message).to_be_visible(timeout=10000)

            # Confirm the content editor placeholder is still shown
            editor_placeholder = page.get_by_text(
                "Chọn một tài liệu từ cây thư mục để xem nội dung."
            )
            expect(editor_placeholder).to_be_visible(timeout=5000)

            # Take the final screenshot for confirmation
            page.screenshot(path="jules-scratch/verification/final-app-state.png")

            print("Final verification screenshot captured successfully.")

        except Exception as e:
            print(f"An error occurred during final verification: {e}")
            page.screenshot(
                path="jules-scratch/verification/final-verification-error.png"
            )
        finally:
            browser.close()


if __name__ == "__main__":
    run_final_verification()
