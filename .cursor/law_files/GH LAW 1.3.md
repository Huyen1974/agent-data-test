**🐙 GH-LAW (Luật về GitHub) – Version 1.3**

**Updated:** August 05, 2025 **Purpose:** Quy định các quy tắc cụ thể
cho việc vận hành trên GitHub trong dự án Agent Data Langroid, tuân thủ
**Hiến pháp v1.11e**. **Scope:** Áp dụng cho các repository
agent-data-test, agent-data-production, và repo trung tâm
chatgpt-githubnew.

**Changes from v1.2:**

- **Bổ sung:** Thêm quy trình báo cáo hàng tuần qua Slack cho các
  artifact cũ, nhằm tăng cường khả năng giám sát và tuân thủ Kế hoạch.

**  **

**Bảng Ánh xạ tới Hiến pháp**

<table>
<colgroup>
<col style="width: 23%" />
<col style="width: 21%" />
<col style="width: 54%" />
</colgroup>
<thead>
<tr>
<th>Mục của GH-LAW</th>
<th>Ánh xạ tới Nguyên tắc Hiến pháp</th>
<th>Rationale (Lý do)</th>
</tr>
</thead>
<tbody>
<tr>
<td>§1: Cấu trúc Repository</td>
<td>HP-01, HP-II</td>
<td>Chuẩn hóa cấu trúc các repository theo mô hình đã được phê
duyệt.</td>
</tr>
<tr>
<td>§2: Quy tắc về Nhánh &amp; Release</td>
<td>HP-IV, Điều VIII</td>
<td>Bảo vệ nhánh main và chuẩn hóa quy trình release để đảm bảo tính ổn
định và tuân thủ WIF.</td>
</tr>
<tr>
<td>§3: Quy trình CI/CD</td>
<td>HP-CI-01, HP-CI-02</td>
<td>Chi tiết hóa các workflow và các bước kiểm tra bắt buộc trong
CI.</td>
</tr>
<tr>
<td>§4: Yêu cầu đối với Pull Request</td>
<td>HP-CS-04</td>
<td>Chuẩn hóa quy trình review code và các quy ước để tăng chất lượng và
tính rõ ràng.</td>
</tr>
<tr>
<td>§5: Quản lý Secrets</td>
<td>HP-05, HP-CS-05</td>
<td>Cụ thể hóa mô hình kỹ thuật cho việc đồng bộ secrets, đảm bảo an
toàn và tuân thủ Hiến pháp.</td>
</tr>
<tr>
<td>§6: Quy tắc Retry của Cursor</td>
<td>HP-CS-02</td>
<td>Chi tiết hóa cơ chế tự sửa lỗi của Cursor.</td>
</tr>
<tr>
<td>§7: Quy trình Dọn dẹp Artifact</td>
<td>HP-CI-03</td>
<td>Mô tả chi tiết workflow tạo và xử lý Issue dọn dẹp artifact.</td>
</tr>
<tr>
<td><strong>§8: Bảo mật</strong></td>
<td><strong>HP-SEC-04</strong></td>
<td><strong>Quy định các bước quét bảo mật và cơ chế bảo vệ mã
nguồn.</strong></td>
</tr>
</tbody>
</table>

**§1: Cấu trúc Repository** 1.1. Các repository chính bao gồm

agent-data-test, agent-data-production, và repo trung tâm
chatgpt-githubnew.

1.2. Cấu trúc thư mục trong mỗi repo BẮT BUỘC phải tuân thủ các quy ước
đã định (ví dụ:

.github/workflows/, terraform/, .cursor/).

**§2: Quy tắc về Nhánh & Release** 2.1.

**Bảo vệ Nhánh main:** Nhánh main BẮT BUỘC phải được bảo vệ với các quy
tắc sau:

\* Yêu cầu Pull Request (PR) để cập nhật.

\* Yêu cầu tối thiểu 1 phê duyệt (approval).

\* Bắt buộc tất cả các status check (context) được định nghĩa tại §3.2
phải thành công.

\* Cấm force push.

2.2.

**Quy ước Định dạng Tag:** Các tag được sử dụng cho việc "Release
Production" BẮT BUỘC phải tuân thủ định dạng Semantic Versioning và có
tiền tố v (ví dụ: v1.0.0, v1.2.3).

2.3.

**Quyền tạo Release Tag:** Chỉ những người có quyền "Maintainer" hoặc
cao hơn mới được phép tạo các tag release trên nhánh main.

**§3: Quy trình CI/CD (Workflows)** 3.1.

**Quy định về Toolchain:** Các workflow có sử dụng Terraform BẮT BUỘC
phải có bước setup-terraform để cài đặt đúng phiên bản ~&gt; 1.8 như đã
quy định trong TF-LAW §8.

3.2.

**Các Status Check Bắt buộc (Pass-gate):** Để một PR được phép merge vào
nhánh main, các status check (context) sau BẮT BUỘC phải thành công
(trạng thái xanh ✅):

\* lint-only \* terraform-plan \* secret-scan \* agent-e2e (hoặc các job
test tương đương) \* manifest-drift-check

**§4: Yêu cầu đối với Pull Request (PR)** 4.1.

**Quy ước Tên nhánh:** Tên nhánh BẮT BUỘC phải tuân thủ quy ước
prefix/description (ví dụ: feat/add-new-tool, fix/bug-123).

4.2.

**Mô tả PR:** Mô tả của PR BẮT BUỘC phải chứa bảng tóm tắt tự động do
Cursor tạo ra theo nguyên tắc HP-CS-04.

**§5: Quản lý Secrets** 5.1.

**Mô hình Kỹ thuật:** Việc đồng bộ secrets từ Google Secret Manager lên
GitHub BẮT BUỘC phải được thực hiện thông qua một workflow
sync-secrets.yml chạy tại repo trung tâm chatgpt-githubnew.

5.2.

**Cơ chế Kích hoạt:** Workflow sync-secrets.yml phải có 2 cơ chế kích
hoạt:

\* Chạy tự động theo lịch (cron) tối thiểu 1 lần/ngày.

\* Chạy thủ công (

workflow\_dispatch) khi cần đồng bộ ngay lập tức.

5.3.

**Cơ chế Xác thực:** Workflow này BẮT BUỘC phải sử dụng một **PAT
(Personal Access Token)** có đủ quyền hạn để ghi secrets (secrets:write)
lên các repo con.

5.4.

**Quyền hạn của Runner:** Runner ở các repo con (agent-data-test,
agent-data-production) BỊ CẤM TUYỆT ĐỐI quyền secrets:write, tuân thủ
HP-CS-05.

5.5.

**Quy trình Xử lý Sự cố (Fallback):** Trong trường hợp quy trình đồng bộ
tự động gặp sự cố kéo dài, việc cập nhật secret thủ công lên repo con
được cho phép, nhưng BẮT BUỘC phải kèm theo một bản ghi kiểm toán (audit
log) ghi rõ lý do, người thực hiện và thời gian.

**§6: Quy tắc Retry và Tự sửa lỗi của Cursor** 6.1. Khi CI thất bại,
Cursor được phép tự động sửa lỗi và push lại cùng nhánh

**tối đa 2 lần**.

6.2. Sau lần retry thứ 2 nếu vẫn thất bại, quy trình BẮT BUỘC phải dừng
lại và thông báo cho Owner.

6.3. Thời gian chờ (cool-down) giữa các lần retry sẽ được quy định chi
tiết trong

CS-LAW.

**§7: Quy trình Dọn dẹp và Giám sát Artifact** 7.1. **Giai đoạn 1 (Cảnh
báo sớm):** Một workflow tự động BẮT BUỘC phải chạy để đánh dấu các
artifact cũ hơn **14 ngày** là "stale". 7.2. **Giai đoạn 2 (Yêu cầu Dọn
dẹp):** Một workflow tự động khác BẮT BUỘC phải được thiết lập để quét
và tạo GitHub Issue \[CLEANUP\]... cho các artifact cũ hơn **30 ngày**.
7.3. **Cơ chế Xác thực:** Các workflow này BẮT BUỘC phải sử dụng một PAT
hoặc GitHub App có đủ quyền hạn cần thiết (ví dụ: issues:write). 7.4.
**Giám sát và Báo cáo:** Một quy trình tự động BẮT BUỘC phải chạy hàng
tuần để tổng hợp số lượng artifact đã được đánh dấu "stale" và gửi báo
cáo qua Slack. Báo cáo này **BẮT BUỘC phải có ngưỡng cảnh báo** (ví dụ:
stale\_count &lt; 5) và sẽ gửi cảnh báo nếu vượt ngưỡng, tuân thủ yêu
cầu trong Plan V12. 7.5. Việc xóa artifact chỉ được thực hiện thủ công
sau khi Issue tương ứng đã được phê duyệt và đóng lại.**
§8: Bảo mật** 8.1.

**Quét Secret:** Mọi Pull Request BẮT BUỘC phải chạy thành công job quét
secret (ví dụ: TruffleHog).

8.2.

**Bảo vệ Workflow:** Thư mục .github/workflows/ BẮT BUỘC phải được bảo
vệ bằng file CODEOWNERS để yêu cầu sự phê duyệt từ người có thẩm quyền
trước khi thay đổi các quy trình CI/CD.

**Phụ lục A – Nợ Kỹ thuật**

<table>
<colgroup>
<col style="width: 7%" />
<col style="width: 22%" />
<col style="width: 58%" />
<col style="width: 10%" />
</colgroup>
<thead>
<tr>
<th>ID Nợ</th>
<th>Hạng mục</th>
<th>Mô tả</th>
<th>Deadline</th>
</tr>
</thead>
<tbody>
<tr>
<td>TD-GH-01</td>
<td>Chuyển sang Organization-Level Secrets</td>
<td>Khi hạ tầng được nâng cấp lên tài khoản GitHub Organization, mô hình
đồng bộ secrets bằng script sẽ được thay thế bằng cơ chế secrets:
inherit của GitHub.</td>
<td>31-12-2025</td>
</tr>
</tbody>
</table>
