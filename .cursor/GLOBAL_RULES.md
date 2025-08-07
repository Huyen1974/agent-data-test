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

- **Yêu cầu về Shell an toàn (Fail-fast Shell):** Mọi bước run: trong
  các workflow GitHub Actions **BẮT BUỘC** phải khai báo shell: bash
  -eou pipefail {0}. Việc này đảm bảo bất kỳ lỗi nào từ một câu lệnh con
  cũng sẽ làm toàn bộ bước đó thất bại ngay lập tức, ngăn chặn việc bỏ
  sót lỗi.

<!-- -->

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

Trước mỗi lệnh git push, bạn bắt buộc phải kiểm tra và vượt qua tất cả
các điều kiện sau:

1.  **Kiểm tra Thư mục làm việc** (Chỉ áp dụng cho môi trường cục bộ)

    - **Lệnh:** pwd

    - **Kết quả mong đợi:** Phải trả về chính xác đường dẫn:
      /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid.

2.  **Kiểm tra Remote Repository**

    - **Lệnh:** git remote get-url origin

    - **Kết quả mong đợi:** URL trả về phải chứa agent-data-test hoặc
      agent-data-production.

3.  **Kiểm tra Terraform cục bộ (Local Terraform Validation)**

    - **Lệnh:** terraform validate (chạy trong các thư mục chứa mã
      Terraform đã thay đổi).

    - **Kết quả mong đợi:** Lệnh phải chạy thành công với mã thoát 0,
      không có lỗi cú pháp.

4.  **Kiểm tra Manifest Drift**

    - **Lệnh:** python scripts/collect_manifest.py --check
      test_manifest_baseline.txt

    - **Kết quả mong đợi:** Lệnh phải chạy thành công với mã thoát 0.
      Nếu có sự thay đổi về số lượng file test chưa được cập nhật, lệnh
      sẽ thất bại và chặn push.

5.  **Kiểm tra Trạng thái Toàn bộ CI trên Nhánh (All-runs Green Check)**

    - **Lưu ý:** Bước này chỉ được thực hiện nếu gh CLI có sẵn.

    - **Lệnh & Logic:**

> CURRENT_BRANCH=\$(git rev-parse --abbrev-ref HEAD)
>
> echo "---"
>
> echo "Checking CI status for all recent runs on branch:
> \$CURRENT_BRANCH"
>
> \# Lấy 5 lần chạy workflow gần nhất, bao gồm tên và kết luận
>
> WORKFLOW_RUNS=\$(gh run list --branch "\$CURRENT_BRANCH" --limit 5
> --json name,conclusion --jq -c '.\[\]')
>
> \# Nếu không có lần chạy nào, coi như PASS
>
> if \[ -z "\$WORKFLOW_RUNS" \]; then
>
> echo "✅ No CI runs found on branch. Check PASSED."
>
> exit 0
>
> fi
>
> \# Duyệt qua từng lần chạy
>
> HAS_FAILURE=false
>
> while IFS= read -r run; do
>
> conclusion=\$(echo "\$run" \| jq -r '.conclusion')
>
> name=\$(echo "\$run" \| jq -r '.name')
>
> \# Kiểm tra nếu kết luận không phải là các trạng thái thành công hoặc
> bỏ qua
>
> if \[\[ "\$conclusion" != "success" && "\$conclusion" != "skipped" &&
> "\$conclusion" != "neutral" \]\]; then
>
> echo "❌ CI FAILED: Workflow '\$name' has conclusion '\$conclusion'."
>
> HAS_FAILURE=true
>
> else
>
> echo "✅ CI PASSED: Workflow '\$name' has conclusion '\$conclusion'."
>
> fi
>
> done \<\<\< "\$WORKFLOW_RUNS"
>
> \# Nếu có bất kỳ lỗi nào, chặn push
>
> if \[ "\$HAS_FAILURE" = true \]; then
>
> echo "---"
>
> echo "🛑 Push blocked due to failed CI runs."
>
> exit 1
>
> fi
>
> echo "---"
>
> echo "All recent CI runs on branch '\$CURRENT_BRANCH' passed. Push
> allowed."
