**GLOBAL_RULES.md (Version 1.2)**

**🌍 QUY TẮC TOÀN CỤC (GLOBAL RULES)**

**Version 1.2**

Tài liệu này định nghĩa các nguyên tắc cốt lõi, bất biến mà bạn phải
tuân thủ trong mọi hoàn cảnh. Các quy tắc này có hiệu lực cao hơn và bổ
trợ cho file quy tắc dự án chi tiết (RULES_agent-data-langroid.md).

**1. Nguyên tắc Phạm vi Duy nhất (Single Scope Principle)**

Bạn chỉ làm việc **duy nhất** trong một bối cảnh đã được định nghĩa.

- **Đường dẫn Dự án Độc quyền:** /Users/nmhuyen/Documents/Manual
  Deploy/agent-data-langroid *(Ghi chú: Quy tắc về đường dẫn chính xác
  này chỉ áp dụng cho môi trường phát triển cục bộ, không áp dụng cho
  các runner CI/CD.)*

- **Cấm tuyệt đối:** Không được đọc, ghi, hay tham chiếu đến bất kỳ dự
  án, repository, hoặc thư mục nào khác ngoài phạm vi đã định.

**2. Nguyên tắc Xác minh Bắt buộc (Mandatory Verification Principle)**

Niềm tin được xây dựng trên kết quả có thể kiểm chứng.

- **Không Báo cáo Sai sự thật:** Trước khi báo cáo một tác vụ là **hoàn
  thành (done/pass)**, bạn BẮT BUỘC phải kiểm tra log, chạy các lệnh xác
  thực, hoặc sử dụng các phương pháp đáng tin cậy khác để đảm bảo kết
  quả là **thành công (success)** trên thực tế.

- **Tránh xác nhận sai bằng mọi giá.**

**3. Nguyên tắc Tự chủ Thực thi (Autonomous Execution Principle)**

Hiệu quả đến từ sự tự chủ trong khuôn khổ.

- **Thực thi đến cùng:** Khi một prompt đã được giao, bạn phải thực thi
  tất cả các tác vụ cho đến khi hoàn thành 100%.

- **Không hỏi xác nhận giữa chừng:** Bạn không được dừng lại để hỏi xác
  nhận hay các câu hỏi không cần thiết.

- **Chỉ dừng lại khi có lỗi chặn (blocking error)** không thể tự giải
  quyết.

- **Lưu ý:** Nguyên tắc này vẫn phải **tuân thủ giới hạn về số lần thử
  lại** và sau khi hết giới hạn, **bạn phải dừng lại và thông báo cho
  Owner** theo quy định trong Project RULES (§8).

**4. Nguyên tắc Tuân thủ & Tự điều chỉnh (Compliance & Self-Correction
Principle)**

Mọi hành động phải tuân thủ luật và có khả năng tự sửa sai.

- **Nguồn Chân lý:** File RULES_agent-data-langroid.md là nguồn chân lý
  duy nhất cho các quy tắc vận hành chi tiết của dự án. Bạn phải tuân
  thủ tuyệt đối các quy tắc trong đó.

- **Cơ chế Tự điều chỉnh khi Thất bại:** Nếu một tác vụ thất bại, trước
  khi thử lại, bạn BẮT BUỘC phải thực hiện quy trình sau:

  1.  **Đối chiếu lại:** So sánh các bước đã thực hiện với các quy tắc
      trong file RULES_agent-data-langroid.md.

  2.  **Phân tích sai lệch:** Xác định xem hành động của bạn có vi phạm
      hay bỏ sót quy tắc nào không.

  3.  **Điều chỉnh cách tiếp cận:** Sửa đổi lại phương pháp thực thi để
      đảm bảo lần thử lại tiếp theo tuân thủ tuyệt đối các quy tắc đã
      định.

**5. Quy trình Tự kiểm tra trước khi Push (Pre-push Self-Check)**

Trước mỗi lệnh git push, bạn phải tự kiểm tra và vượt qua các điều kiện
sau:

1.  **Kiểm tra Thư mục làm việc (Chỉ áp dụng cho môi trường cục bộ):**

    - **Lệnh:** pwd

    - **Kết quả mong đợi:** Phải trả về chính xác đường dẫn:
      /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid.

2.  **Kiểm tra Remote Repository:**

    - **Lệnh:** git remote get-url origin

    - **Kết quả mong đợi:** URL trả về phải chứa agent-data-test hoặc
      agent-data-production.

3.  **Kiểm tra Trạng thái CI trên Nhánh hiện tại (Logic cải tiến):**

    - **Lưu ý:** Bước này chỉ được thực hiện nếu gh CLI có sẵn. Nếu
      không, bước này sẽ được bỏ qua.

    - **Bước 1: Lấy tên nhánh hiện tại.**

      - CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

    - **Bước 2: Kiểm tra Manifest Drift.**

      - **Lệnh:** python scripts/collect_manifest.py --check
        test_manifest_baseline.txt

      - **Kết quả mong đợi:** Lệnh phải chạy thành công với mã thoát 0.
        Nếu thất bại, **dừng push**.

    - **Bước 3: Lấy trạng thái của lần chạy CI gần nhất trên nhánh đó.**

      - LAST_RUN_STATUS=$(gh run list --branch $CURRENT_BRANCH
        --limit 1 --json conclusion --jq '.[0].conclusion')

    - **Bước 4: Kiểm tra điều kiện.**

      - **Nếu LAST_RUN_STATUS rỗng (chưa có CI nào chạy):** Kiểm tra
        được coi là **PASS**.

      - **Nếu LAST_RUN_STATUS là success:** Kiểm tra được coi là
        **PASS**.

      - **Nếu LAST_RUN_STATUS là failure (hoặc trạng thái lỗi khác):**

        - Kiểm tra message của commit gần nhất: git log -1 --pretty=%B.

        - Nếu message chứa tag [ci-fix], kiểm tra được coi là **PASS**
          (cho phép push để sửa lỗi CI).

        - Nếu không, kiểm tra **FAIL** và bạn không được phép push.
