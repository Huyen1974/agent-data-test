**⛅ GC-LAW (Luật về Google Cloud) – Version 1.4 (Phiên bản Hoàn chỉnh
Cuối cùng)**

**Updated:** August 05, 2025 **Purpose:** Quy định các quy tắc cụ thể
cho việc vận hành trên Google Cloud, tuân thủ **Hiến pháp v1.11e**.
**Scope:** Toàn bộ tài nguyên trên Google Cloud Platform được quản lý
bởi dự án Agent Data Langroid.

**Changes from v1.3:**

- Cập nhật toàn bộ Luật để phản ánh mô hình **1 Project duy nhất** và
  các quy tắc mới nhất từ Hiến pháp v1.11e.

- **Bổ sung lại các ví dụ, ghi chú chi tiết, và phần giải thích bối cảnh
  từ các phiên bản trước để tăng tính rõ ràng và đầy đủ.**

**Bảng Ánh xạ tới Hiến pháp**

<table>
<colgroup>
<col style="width: 22%" />
<col style="width: 21%" />
<col style="width: 55%" />
</colgroup>
<thead>
<tr>
<th>Mục của GC-LAW</th>
<th>Ánh xạ tới Nguyên tắc Hiến pháp</th>
<th><strong>Rationale (Lý do)</strong></th>
</tr>
</thead>
<tbody>
<tr>
<td>§1: Cấu trúc Project</td>
<td>HP-01, HP-II</td>
<td>Chi tiết hóa mô hình 1 Project duy nhất đã được Hiến pháp phê
duyệt.</td>
</tr>
<tr>
<td>§2: Quản lý Truy cập (IAM &amp; WIF)</td>
<td>HP-III, Điều VIII</td>
<td>Chuẩn hóa các điều kiện WIF để ngăn lỗi xác thực, tuân thủ bảng điều
kiện trong Hiến pháp.</td>
</tr>
<tr>
<td>§3: Quản lý Secrets</td>
<td>HP-05, HP-SEC-02</td>
<td>Cụ thể hóa mô hình đồng bộ secrets từ Google Secret Manager theo
đúng nguyên tắc của Hiến pháp.</td>
</tr>
<tr>
<td>§4: Quản lý Lưu trữ</td>
<td>HP-II, HP-CI-03, HP-DR-01</td>
<td>Áp dụng quy ước đặt tên và vòng đời tài nguyên đã được chốt trong
Hiến pháp.</td>
</tr>
<tr>
<td>§5: Chính sách Vùng</td>
<td>HP-II (Qdrant Cluster)</td>
<td>Quy định vùng hoạt động mặc định và các ngoại lệ đã được phê
duyệt.</td>
</tr>
<tr>
<td>§6: Quản lý Chi phí &amp; Giám sát</td>
<td>HP-OBS-01, HP-COST-01</td>
<td>Cụ thể hóa các yêu cầu về giám sát và kiểm soát chi phí.</td>
</tr>
<tr>
<td>§7: Phục hồi Thảm họa (DR)</td>
<td>HP-DR-01</td>
<td>Chi tiết hóa các yêu cầu tối thiểu về tần suất và đích đến của bản
sao lưu.</td>
</tr>
<tr>
<td><strong>§8: Bài học Kinh nghiệm</strong></td>
<td><strong>HP-III, HP-IV</strong></td>
<td><strong>Ghi lại bối cảnh và lý do ra đời của các quy tắc WIF để
tránh lặp lại lỗi trong quá khứ.</strong></td>
</tr>
<tr>
<td><strong>Phụ lục A: Ranh giới Logic</strong></td>
<td><strong>HP-01, HP-II</strong></td>
<td><strong>Làm rõ cách phân tách môi trường Test/Prod trong cùng một
Project.</strong></td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

**§1: Cấu trúc Project** 1.1. Toàn bộ hạ tầng của dự án (bao gồm cả môi
trường Test và Production) BẮT BUỘC phải được triển khai trên

**một Project Google Cloud duy nhất**.

1.2. Project ID được phê duyệt là:

github-chatgpt-ggcloud.

1.3. Service Account duy nhất được phê duyệt là:

chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com.

**§2: Quản lý Truy cập (IAM & WIF)**

2.1. Workload Identity Federation (WIF) là phương thức xác thực chính
cho các quy trình CI/CD.

2.2. Bảng Điều kiện WIF Chuẩn hóa BẮT BUỘC phải được cấu hình trong
Terraform và tuân thủ tuyệt đối bảng đã được phê duyệt trong **Điều VIII
của Hiến pháp v1.11e**.

2.3. **Hướng dẫn Triển khai và Di dời:** \* **Terraform:** Cấu hình BẮT
BUỘC phải được quản lý bằng code. Ví dụ:

resource "google\_iam\_workload\_identity\_pool\_provider" "github" {
... attribute\_condition = "..." } .

\* **Di dời Provider cũ:** Lệnh gcloud iam workload-identity-pools
providers update-oidc... sẽ được sử dụng để di dời các provider cũ sang
cấu hình chuẩn.

\* **Kiểm tra cục bộ:**
- Trước khi đẩy lên CI, lập trình viên nên kiểm tra điều kiện WIF bằng
lệnh gcloud auth application-default login
--impersonate-service-account=\[SA\] để xác thực quyền.
- **Xác thực Token:** Để kiểm tra sâu hơn, có thể lấy và xác thực token
bằng các lệnh tương tự như sau: gcloud sts get-token
--audience="\[AUDIENCE\]"

**§3: Quản lý Secrets**

3.1. **Nguồn Chân lý (Source of Truth):** Google Secret Manager là nơi
lưu trữ giá trị gốc và duy nhất của tất cả các secret.

3.2. **Mô hình Đồng bộ:** Việc đồng bộ secrets từ Google Secret Manager
lên GitHub BẮT BUỘC phải tuân thủ mô hình đã quy định tại **HP-05 của
Hiến pháp v1.11e** (sử dụng repo trung tâm và script đồng bộ cho tài
khoản cá nhân).

3.3. **Ví dụ Di dời Secret:** gh secret set &lt;SECRET\_NAME&gt; -b
"&lt;value&gt;" --repo Huyen1974/chatgpt-githubnew.

**§4: Quản lý Lưu trữ (GCS & Artifact Registry)**

4.1. **Quy ước Đặt tên Bucket:** Mọi GCS Bucket BẮT BUỘC phải tuân thủ
quy ước đặt tên
&lt;standard-prefix&gt;-agent-data-&lt;purpose&gt;-&lt;env&gt; như đã
quy định tại Điều II của Hiến pháp và được chi tiết hóa trong TF-LAW.

4.2. **Vòng đời Artifact:** Việc quản lý các artifact cũ (&gt; 30 ngày)
BẮT BUỘC phải tuân thủ quy trình đã quy định tại **HP-CI-03 của Hiến
pháp v1.11e** (tạo GitHub Issue để phê duyệt và xóa thủ công).

**4.3. Chính sách Truy cập Bucket:** Mọi GCS Bucket được tạo mới BẮT
BUỘC phải bật uniform\_bucket\_level\_access = true, tuân thủ nguyên tắc
HP-02 của Hiến pháp và được thực thi tại TF-LAW §4.3.

**§5: Chính sách Vùng (Region Policy)**

5.1. **Vùng mặc định:** asia-southeast1 (Singapore) được chỉ định là
vùng mặc định cho tất cả các tài nguyên, trừ khi có ngoại lệ được ghi
rõ. Cấu hình Terraform NÊN mã hóa cứng giá trị này trong file

tfvars cho các tài nguyên không phải Qdrant.

5.2. **Ngoại lệ Qdrant:** Cluster Qdrant được phép triển khai tại
us-east4 cho đến khi có thông báo chính thức về việc hỗ trợ tại
Singapore.

**§6: Quản lý Chi phí & Giám sát**

6.1. **Cảnh báo Ngân sách:** BẮT BUỘC phải được cấu hình theo nguyên tắc
**HP-COST-01**.

6.2. **Gán nhãn (Labeling):** Mọi tài nguyên được tạo ra BẮT BUỘC phải
được gán nhãn đầy đủ (project, environment, service) để phục vụ việc
giám sát và kiểm soát chi phí.

6.3. **Giám sát (Observability):** Việc triển khai dashboard giám sát
BẮT BUỘC phải tuân thủ nguyên tắc **HP-OBS-01**.

**§7: Phục hồi Thảm họa (Disaster Recovery)**

7.1. **Nguyên tắc chung:** Cơ chế sao lưu (backup/snapshot) tự động cho
các dữ liệu quan trọng BẮT BUỘC phải được thiết lập theo nguyên tắc
**HP-DR-01** của Hiến pháp.

7.2. **Tần suất Sao lưu Tối thiểu:**

\* Môi trường Production: Dữ liệu BẮT BUỘC phải được sao lưu tối thiểu
**1 lần/ngày**.

\* Môi trường Test: Dữ liệu BẮT BUỘC phải được sao lưu tối thiểu **1
lần/tuần**.

7.3. **Đích đến của Bản sao lưu:** \* Tất cả các bản sao lưu BẮT BUỘC
phải được lưu trữ trong GCS Bucket dành riêng cho việc sao lưu.

\* Bucket này phải tuân thủ quy ước đặt tên đã được định nghĩa trong
TF-LAW:

&lt;standard-prefix&gt;-agent-data-backup-&lt;env&gt;.

**§8: Bài học Kinh nghiệm** 8.1. Các quy tắc WIF trong §2 được tạo ra để
khắc phục triệt để lỗi unauthorized\_client đã gây ra sự chậm trễ đáng
kể trong quá khứ. Nguyên nhân gốc rễ là do điều kiện WIF cũ chỉ cho phép
CI chạy trên nhánh main, làm thất bại tất cả các quy trình chạy trên các
nhánh feature hoặc Pull Request. Việc chuẩn hóa điều kiện cho phép
refs/heads/ là bắt buộc để đảm bảo CI hoạt động thông suốt.

**Phụ lục A – Ranh giới Logic giữa Test và Production**

*Bảng này làm rõ cách các tài nguyên được phân tách một cách logic trong
cùng một Project Google Cloud.*

<table>
<colgroup>
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 59%" />
</colgroup>
<thead>
<tr>
<th>Tài nguyên</th>
<th>Cách phân tách</th>
<th>Ví dụ</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>GCS Bucket</strong></td>
<td>Hậu tố -&lt;env&gt;</td>
<td>...-artifacts-test vs. ...-artifacts-production</td>
</tr>
<tr>
<td><strong>Artifact Registry</strong></td>
<td>Tên repo riêng</td>
<td>.../agent-data-test vs. .../agent-data-production</td>
</tr>
<tr>
<td><strong>Qdrant Collection</strong></td>
<td>Tên collection riêng</td>
<td>test_documents vs. production_documents</td>
</tr>
<tr>
<td><strong>Cloud Run Service</strong></td>
<td>Tên service riêng</td>
<td>agent-data-test-service vs. agent-data-prod-service</td>
</tr>
</tbody>
</table>
