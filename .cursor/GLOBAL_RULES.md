**GLOBAL_RULES.md (Version 1.2)**

**🌍 QUY TẮC TOÀN CỤC (GLOBAL RULES)**

**Version 1.2**

Tài liệu này định nghĩa các nguyên tắc cốt lõi, bất biến mà bạn phải tuân thủ trong mọi hoàn cảnh. Các quy tắc này có hiệu lực cao hơn và bổ trợ cho file quy tắc dự án chi tiết (RULES_agent-data-langroid.md).

**1. Nguyên tắc Phạm vi Duy nhất (Single Scope Principle)**

Bạn chỉ làm việc **duy nhất** trong một bối cảnh đã được định nghĩa.

- **Đường dẫn Dự án Độc quyền:** /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid *(Ghi chú: Quy tắc về đường dẫn chính xác này chỉ áp dụng cho môi trường phát triển cục bộ, không áp dụng cho các runner CI/CD.)*

- **Cấm tuyệt đối:** Không được đọc, ghi, hay tham chiếu đến bất kỳ dự án, repository, hoặc thư mục nào khác ngoài phạm vi đã định.

- Ghi chú về sự Tương quan với Project Rules: Để đảm bảo tính toàn vẹn của quy trình CI/CD, bạn **BẮT BUỘC** phải tuân thủ kiến trúc **"Một cửa - Pass Gate"** được định nghĩa chi tiết trong RULES_agent-data-langroid.md (Mục 5). Nguyên tắc này quy định chỉ có duy nhất một status check được phép làm cổng kiểm soát (Required check), các job kiểm tra khác phải được gọi qua workflow_call để tạo ra một tín hiệu pass/fail tổng thể duy nhất, rõ ràng.

**2. Nguyên tắc Xác minh Bắt buộc (Mandatory Verification Principle)**

**2.1 Post-push CI Verification (HARD-BLOCK)**

Sau mỗi lần push hoặc mở/cập nhật Pull Request, bạn BẮT BUỘC phải thực thi quy trình xác minh CI một cách nghiêm ngặt:

- **Bước A: Lấy RUN_ID của run mới nhất, không bị hủy, theo commit SHA.**

> Bạn phải xác định RUN_ID của workflow được kích hoạt bởi chính commit SHA bạn vừa push. Logic **BẮT BUỘC** phải lọc bỏ các run đã bị hủy (conclusion: "cancelled") và chỉ chọn run đã hoàn thành (status: "completed") được tạo gần nhất. Cấm watch một cách chung chung.

- **Lệnh tham khảo:**

> SHA=\$(git rev-parse HEAD)
>
> RUN_ID=\$(gh run list --commit "\$SHA" --json databaseId,conclusion,status,createdAt --jq 'map(select(.status == "completed" and .conclusion != "cancelled")) \| sort_by(.createdAt) \| .\[-1\].databaseId' -q)

- **Bước B: Theo dõi và chờ kết quả.**

1.  Sử dụng RUN_ID đã xác định để theo dõi cho đến khi workflow kết thúc.

2.  Lệnh bắt buộc: gh run watch "\$RUN_ID" --exit-status

3.  Nếu lệnh trên thất bại (CI đỏ), bạn phải chuyển sang **Bước C**.

- **Bước B.1: Xử lý trường hợp Run bị hủy do Push mới.** Nếu lệnh gh run watch ở Bước B thất bại với trạng thái cancelled, đây không được tính là một vòng auto-fix. Bạn **BẮT BUỘC** phải quay lại **Bước A** để lấy RUN_ID của run mới nhất và theo dõi lại.

- **Bước C: Phân tích lỗi và tự động sửa chữa (Tối đa 2 vòng).**

1.  **Đọc log và lưu lại:** Dùng RUN_ID để lấy log của job thất bại và lưu vào file có định danh theo SHA và vòng lặp sửa lỗi (\<N\> là 1 hoặc 2).

- **Lệnh tham khảo:** gh run view "\$RUN_ID" --log-failed \> ".ci/\${SHA}.autofix\<N\>.log"

- **Ghi chú quan trọng:** Các file log này chỉ dùng cho mục đích phân tích cục bộ, **BẮT BUỘC** phải được thêm vào .gitignore và **CẤM TUYỆT ĐỐI** commit vào repository. Quy trình CI/CD sẽ lưu trữ log bằng cách upload artifact theo quy định tại PROJECT RULES - mục 5.9 .

2.  Chờ 5 phút (Cool-down): **Trước khi push bản sửa lỗi, bạn** BẮT BUỘC **phải chờ 5 phút.**

- **Lệnh bắt buộc:** sleep 300

3.  Commit bản sửa lỗi: Commit phải chứa nhãn \[AUTOFIX-1\] và \[AUTOFIX-2\] tương ứng với mỗi vòng sửa.

4.  Lặp lại quy trình: Lặp lại từ Bước A cho vòng sửa lỗi thứ hai.

- **Bước D: Điều kiện báo cáo "DONE".**

1.  Bạn **CẤM TUYỆT ĐỐI** báo cáo "DONE" hoặc "COMPLETE" cho tác vụ nếu conclusion của RUN_ID tương ứng với commit SHA cuối cùng không phải là success.

- **Bước E: Chuẩn hóa Múi giờ.**

1.  Mọi hoạt động so khớp, theo dõi CI và phân tích log liên quan đến thời gian đều phải được thực hiện theo múi giờ **UTC** để đảm bảo tính nhất quán.

**2.2 Niềm tin được xây dựng trên kết quả có thể kiểm chứng**

- **Yêu cầu Shell an toàn (Fail-fast Shell)**:
Tất cả bước run: trong workflow GitHub Actions **BẮT BUỘC** phải khai báo:

> yaml
>
> Sao chép
>
> shell: bash -euo pipefail {0}
>
> để mọi lỗi từ câu lệnh con sẽ khiến bước thất bại ngay, tránh bỏ sót lỗi.

- **Không Báo cáo Sai sự thật**:
Trước khi báo một tác vụ là hoàn thành (done/pass), **BẮT BUỘC** phải:

- Kiểm tra log chi tiết.

- Chạy lệnh xác thực hoặc các phương pháp đáng tin cậy khác.

- Đảm bảo kết quả thật sự **success** trên thực tế.

- **Tránh xác nhận sai bằng mọi giá**.

**2.3 Nguyên tắc Ngoại lệ Hợp lệ (Valid Exception Principle)**

- **Bối cảnh:** Quy tắc này được áp dụng trong các trạng thái vận hành đặc biệt, ví dụ như khi một tài nguyên dùng chung (như cluster Qdrant) được tạm dừng chủ động để tối ưu chi phí.

- **Quy định:**

- Trong trạng thái này, các job CI/CD phụ thuộc trực tiếp vào tài nguyên đó **ĐƯỢC PHÉP** thất bại hoặc bị bỏ qua (skipped) mà không làm toàn bộ workflow bị đánh dấu là đỏ.

- Ngoại lệ này chỉ hợp lệ khi và chỉ khi Pull Request đang được kiểm tra **KHÔNG** chứa bất kỳ thay đổi nào trong các đường dẫn file được xem là "liên quan đến Qdrant". Các đường dẫn bao gồm (nhưng không giới hạn): functions/manage_qdrant/\*\*, terraform/\*\*/qdrant\*, infra/qdrant/\*\*, scripts/qdrant\*.

- **Trách nhiệm:** Owner có trách nhiệm kích hoạt lại tài nguyên trước khi thực hiện merge hoặc các tác vụ yêu cầu sự sẵn sàng của tài nguyên đó.

- (Quy định chi tiết về việc áp dụng ngoại lệ này trong workflow pass-gate được làm rõ tại PROJECT RULES - mục 4.1).

**3. Nguyên tắc Tự chủ Thực thi (Autonomous Execution Principle)**

Hiệu quả đến từ sự tự chủ trong khuôn khổ.

- Thực thi đến cùng: Khi một prompt đã được giao, bạn phải thực thi tất cả các tác vụ cho đến khi hoàn thành 100%.

- Không hỏi xác nhận giữa chừng: Bạn không được dừng lại để hỏi xác nhận hay các câu hỏi không cần thiết.

- Chỉ dừng lại khi có lỗi chặn (blocking error) không thể tự giải quyết.

- Lưu ý: Nguyên tắc này vẫn phải tuân thủ giới hạn về số lần thử lại và sau khi hết giới hạn, bạn phải dừng lại và thông báo cho Owner theo quy định trong Project RULES (§8).

**4. Nguyên tắc Tuân thủ & Tự điều chỉnh (Compliance & Self-Correction Principle)**

Mọi hành động phải tuân thủ luật và có khả năng tự sửa sai.

- Nguồn Chân lý: File RULES_agent-data-langroid.md là nguồn chân lý duy nhất cho các quy tắc vận hành chi tiết của dự án. Bạn phải tuân thủ tuyệt đối các quy tắc trong đó.

- Cơ chế Tự điều chỉnh khi Thất bại: Nếu một tác vụ thất bại, trước khi thử lại, bạn BẮT BUỘC phải thực hiện quy trình sau:

1.  Đối chiếu lại: So sánh các bước đã thực hiện với các quy tắc trong file RULES_agent-data-langroid.md.

2.  Phân tích sai lệch: Xác định xem hành động của bạn có vi phạm hay bỏ sót quy tắc nào không.

3.  Điều chỉnh cách tiếp cận: Sửa đổi lại phương pháp thực thi để đảm bảo lần thử lại tiếp theo tuân thủ tuyệt đối các quy tắc đã định.

**5. Quy trình Tự kiểm tra trước khi Push (Pre-push Self-Check)**

Trước mỗi lệnh git push, bạn bắt buộc phải vượt qua toàn bộ các kiểm tra sau:

5.0 Kiểm tra Công cụ Bắt buộc (Toolchain Verification)

- **Lệnh:**

> command -v gh \>/dev/null 2\>&1 \|\| { echo "Lỗi: 'gh' CLI chưa được cài đặt."; exit 1; }
>
> command -v jq \>/dev/null 2\>&1 \|\| { echo "Lỗi: 'jq' chưa được cài đặt."; exit 1; }
>
> gh auth status \>/dev/null 2\>&1 \|\| { echo "Lỗi: 'gh' CLI chưa được xác thực. Hãy chạy 'gh auth login'."; exit 1; }

- **Kết quả mong đợi:** Script chạy thành công. Nếu thiếu công cụ, phải dừng lại và báo lỗi.

5.1 Kiểm tra Thư mục Làm việc (Scope Check - LOCAL only)

> \- Lệnh:
>
> pwd

Kết quả mong đợi:

> /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid

5.2 Kiểm tra Remote Repository

Lệnh:

git remote get-url origin

Kết quả mong đợi:

URL chứa: agent-data-test hoặc agent-data-production

5.3 Kiểm tra Terraform Cục bộ (Local Terraform Validate)

- **Lệnh:**

> terraform init -backend=false -input=false && terraform validate -no-color

- **Kết quả mong đợi:** Cả hai lệnh init và validate đều phải chạy thành công với mã thoát 0.

5.4 Kiểm tra Manifest Drift (Test Count Control)

- **Lệnh:** python scripts/collect_manifest.py --check test_manifest_baseline.txt

- **Kết quả mong đợi:** Mã thoát = 0.

**
5.5 Kiểm tra CI của Commit SHA Hiện Tại (Accurate CI Check)**

Bắt buộc nếu gh CLI có sẵn. Quy trình này chỉ kiểm tra trạng thái của **run CI mới nhất, đã hoàn thành và không bị hủy** tương ứng với commit SHA hiện tại.

- **Lệnh & Logic:**

> CURRENT_SHA=\$(git rev-parse HEAD)
>
> \# Lấy run mới nhất, đã hoàn thành và không bị hủy, của SHA hiện tại
>
> LATEST_RUN=\$(gh run list --commit "\$CURRENT_SHA" --json name,conclusion,status,createdAt --jq 'map(select(.status=="completed" and .conclusion!="cancelled")) \| sort_by(.createdAt) \| .\[-1\]')
>
> if \[ -z "\$LATEST_RUN" \] \|\| \[ "\$LATEST_RUN" == "null" \]; then
>
> echo "✅ No valid CI runs found for current SHA. Push allowed."
>
> exit 0
>
> fi
>
> CONCLUSION=\$(echo "\$LATEST_RUN" \| jq -r '.conclusion')
>
> NAME=\$(echo "\$LATEST_RUN" \| jq -r '.name')
>
> if \[\[ "\$CONCLUSION" == "failure" \|\| "\$CONCLUSION" == "timed_out" \]\]; then
>
> echo "❌ \$NAME =\> \$CONCLUSION"
>
> echo "🛑 Push blocked - run CI mới nhất của SHA hiện tại đã thất bại."
>
> exit 1
>
> fi
>
> echo "✅ Latest CI run for current SHA passed (\$NAME =\> \$CONCLUSION)."

- **🎯 Lưu ý:**

- Quy trình này chủ động lọc các run đã **hoàn thành** (status=="completed") và có kết luận **không phải bị hủy** (conclusion!="cancelled") để chỉ lấy kết quả của lần chạy cuối cùng.

- Logic này ngăn chặn việc push bị chặn nhầm bởi các run cũ đã thất bại nhưng sau đó được sửa bằng một run mới thành công cho cùng một commit.
