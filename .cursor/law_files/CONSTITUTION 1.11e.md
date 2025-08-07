**📜 Hiến Pháp Hạ Tầng Agent Data – Version 1.11e (Final Freeze)**

**Updated:** August 04, 2025 **Purpose:** Supreme principles governing
Agent Data Langroid. All Laws and plans MUST comply. **Scope:**
agent-data-test / agent-data-production **Changes from v1.11d:**

- **v1.11e:** Tinh chỉnh cuối cùng về mô hình secrets cho phù hợp với
  thực tế hạ tầng, ràng buộc định dạng của tiền tố bucket, và tự động
  hóa hoàn toàn quy trình dọn dẹp artifact sau khi được phê duyệt. Đây
  là bản đóng băng cuối cùng.

**Điều I – Phạm vi & Mục tiêu**

<table>
<colgroup>
<col style="width: 5%" />
<col style="width: 14%" />
<col style="width: 56%" />
<col style="width: 23%" />
</colgroup>
<thead>
<tr>
<th>ID</th>
<th>Principle</th>
<th>Description</th>
<th>Source Documents / Notes</th>
</tr>
</thead>
<tbody>
<tr>
<td>HP-01</td>
<td>Single Owner Simplicity</td>
<td>Single owner manages infrastructure for minimal, observable
configs.</td>
<td>HẠ TẦNG GOOGLE CLOUD.docx (reflects single project
architecture)</td>
</tr>
<tr>
<td>HP-02</td>
<td>Absolute IaC with Minimalism</td>
<td>All resources via Terraform; Terraform quản lý khai báo secret
(metadata), giá trị cụ thể được inject thủ công / CI, không hard-code
trong HCL. <strong>Tất cả các GCS Bucket được tạo mới BẮT BUỘC phải bật
uniform_bucket_level_access.</strong></td>
<td>HẠ TẦNG GOOGLE CLOUD.docx, QDRANT INFO &amp; Requirement.docx</td>
</tr>
<tr>
<td>HP-03</td>
<td>No False Reporting</td>
<td>No “PASS/Complete” unless conclusion == success verified by CI
logs.</td>
<td>Plan checkpoint V7.docx, 0.6b1-fix9</td>
</tr>
<tr>
<td>HP-04</td>
<td>Automated Test Count Control</td>
<td>Hệ thống tự động kiểm soát sự thay đổi về số lượng bài kiểm tra. Mọi
thay đổi (thêm/bớt test) phải được phản ánh một cách tường minh thông
qua việc cập nhật file "manifest" (test_manifest_baseline.txt). CI sẽ tự
động thất bại nếu phát hiện có sự thay đổi chưa được ghi nhận (Manifest
Drift ≠ 0).</td>
<td>Plan checkpoint V7.docx (CP0.4), o3 gap, User chốt cuối</td>
</tr>
<tr>
<td>HP-05</td>
<td>Central Secrets Inheritance</td>
<td>Mô hình quản lý secrets được chuẩn hóa là quản lý tập trung, sử dụng
một repo trung tâm (ví dụ: chatgpt-githubnew) để điều phối việc đồng bộ
secrets từ Google Secret Manager sang các repo con thông qua script. Khi
hạ tầng được nâng cấp lên tài khoản GitHub Organization, mô hình sẽ
chuyển sang sử dụng Organization-Level secrets.<br />
Trong trường hợp quy trình đồng bộ tự động gặp sự cố kéo dài (ví dụ:
&gt;24 giờ), Owner được phép cập nhật secret thủ công tại repo trung
tâm, với điều kiện bắt buộc phải có bản ghi kiểm toán (audit log) chi
tiết.</td>
<td>HẠ TẦNG GOOGLE CLOUD.docx, o3 X-2, user decision, o3 edit</td>
</tr>
</tbody>
</table>

**Điều II – Quy ước Định danh Chung**

<table>
<colgroup>
<col style="width: 8%" />
<col style="width: 25%" />
<col style="width: 22%" />
<col style="width: 43%" />
</colgroup>
<thead>
<tr>
<th>Resource</th>
<th>Standard Naming</th>
<th>Example</th>
<th>Notes</th>
</tr>
</thead>
<tbody>
<tr>
<td>GCP Project</td>
<td>github-chatgpt-ggcloud</td>
<td></td>
<td>Dùng chung cho cả test/prod theo quyết định cuối cùng.</td>
</tr>
<tr>
<td>Service Account</td>
<td>chatgpt-deployer@&lt;project&gt;.iam.gserviceaccount.com</td>
<td>chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com</td>
<td>Least privilege. <strong>Đây là Service Account duy nhất được sử
dụng. Cấm tạo SA mới trừ khi có sự sửa đổi Hiến pháp.</strong></td>
</tr>
<tr>
<td>WIF Pool</td>
<td>agent-data-pool</td>
<td></td>
<td>Single pool.</td>
</tr>
<tr>
<td>WIF Provider</td>
<td>github-provider</td>
<td></td>
<td>Attribute conditions per repo, có kế hoạch di dời provider cũ.</td>
</tr>
<tr>
<td>GCS Bucket</td>
<td>&lt;standard-prefix&gt;/agent-data-&lt;purpose&gt;-&lt;env&gt;</td>
<td>huyen1974-agent-data-artifacts-test</td>
<td><p>Tiền tố chuẩn hóa (&lt;standard-prefix&gt;) được định nghĩa và
quản lý trong TF-LAW, với giá trị mặc định là huyen1974. Tiền tố này BẮT
BUỘC phải tuân thủ định dạng tên miền DNS (RFC 1035). <em>Ghi chú:
&lt;purpose&gt; là mục đích sử dụng (ví dụ: artifacts, tfstate, backup);
&lt;env&gt; là môi trường (test hoặc production).</em></p>
<p>&lt;br&gt;</p>
<p><strong>Nguyên tắc chung về định danh:</strong></p>
<ul>
<li><p><strong>Tài nguyên công khai</strong> (Bucket, Repo, Project ID):
Bắt buộc chỉ dùng dấu gạch ngang (-).</p></li>
<li><p><strong>Tài nguyên nội bộ</strong> (Secret ID, Qdrant
Collection): Được phép dùng cả gạch ngang (-) và gạch dưới (_).</p></li>
</ul>
<p>&lt;br&gt;</p>
<p><strong>Ngoại lệ:</strong> Các bucket do Google Cloud tự sinh (vd:
gcf-v2-sources*, artifacts.*.appspot.com) không thuộc phạm vi của quy
ước này.</p></td>
</tr>
<tr>
<td>Qdrant Cluster</td>
<td>agent-data-vector-dev-useast4</td>
<td></td>
<td>Shared cluster for development.</td>
</tr>
<tr>
<td>Qdrant Collection</td>
<td>&lt;env&gt;_documents</td>
<td>test_documents, production_documents</td>
<td>Phân tách trong cluster dùng chung.</td>
</tr>
<tr>
<td>GitHub Repos</td>
<td>agent-data-&lt;env&gt;</td>
<td>agent-data-test, agent-data-production</td>
<td></td>
</tr>
<tr>
<td>Secrets (GCP)</td>
<td>&lt;purpose&gt;_&lt;env&gt;</td>
<td>Qdrant_agent_data_N1D8R2vC0_5</td>
<td>Nguồn gốc tại Secret Manager, tham chiếu từ nguồn tập trung.</td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

**Điều III – Chính sách Bảo mật & Quyền hạn**

<table>
<colgroup>
<col style="width: 14%" />
<col style="width: 18%" />
<col style="width: 67%" />
</colgroup>
<thead>
<tr>
<th>ID</th>
<th>Principle</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>HP-SEC-01</td>
<td>Least Privilege</td>
<td>Only necessary roles; prohibit admin roles.</td>
</tr>
<tr>
<td>HP-SEC-02</td>
<td>Secret Rotation</td>
<td>Rotate keys every 90 days for production; 120 days for test.</td>
</tr>
<tr>
<td>HP-SEC-03</td>
<td>Audit Logging</td>
<td>Enable Cloud Audit Logs for DATA_WRITE.</td>
</tr>
<tr>
<td>HP-SEC-04</td>
<td>Secret Scanning</td>
<td>Zero findings via TruffleHog.</td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

**Điều IV – Kiểm soát CI/CD**

<table>
<colgroup>
<col style="width: 6%" />
<col style="width: 15%" />
<col style="width: 77%" />
</colgroup>
<thead>
<tr>
<th>ID</th>
<th>Principle</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>HP-CI-01</td>
<td>Mandatory Checks</td>
<td>Include lint-only, agent-e2e, terraform-plan, secret-scan; all must
succeed.</td>
</tr>
<tr>
<td>HP-CI-02</td>
<td>Pass Gate</td>
<td>Verify combined status before merge.</td>
</tr>
<tr>
<td>HP-CI-03</td>
<td>Artifact Retention</td>
<td><p>Các artifact cũ phải được quản lý vòng đời theo quy trình 2 giai
đoạn:</p>
<ol type="1">
<li><p><strong>Sau 14 ngày:</strong> Các artifact sẽ được tự động đánh
dấu là "stale" (cũ) để cảnh báo sớm.</p></li>
<li><p><strong>Sau 30 ngày:</strong> Một quy trình tự động sẽ tạo GitHub
Issue [CLEANUP]... để yêu cầu phê duyệt. Việc xóa bỏ sẽ được thực hiện
thủ công bởi người có thẩm quyền sau khi Issue được đóng lại.</p></li>
</ol></td>
</tr>
<tr>
<td>HP-CI-04</td>
<td>No Continue-on-Error</td>
<td>Prohibit in test/lint/validate jobs, except for auth fallback.</td>
</tr>
<tr>
<td>HP-CI-05</td>
<td>Rollback &amp; Fallback</td>
<td><strong>Roadmap ≥ 0.7 BẮT BUỘC phải cung cấp cơ chế rollback tự
động;</strong> trước thời điểm đó, việc rollback được phép thực hiện thủ
công.</td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

**Điều V – Quản lý Chi phí & Giám sát**

<table>
<colgroup>
<col style="width: 10%" />
<col style="width: 14%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr>
<th>ID</th>
<th>Principle</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>HP-COST-01</td>
<td>Budget Alerts</td>
<td>Budget alerts phải được cấu hình ở các ngưỡng 50%/80%/100%.</td>
</tr>
<tr>
<td>HP-OBS-01</td>
<td>Observability</td>
<td>Hệ thống BẮT BUỘC phải có dashboard giám sát các chỉ số vận hành cốt
lõi (VD: độ trễ truy vấn, chi phí CI/CD). Chi tiết về chỉ số sẽ được quy
định trong Luật.</td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

**Điều VI – Quản lý Dữ liệu & Phục hồi Thảm họa (DR)**

<table>
<colgroup>
<col style="width: 6%" />
<col style="width: 12%" />
<col style="width: 81%" />
</colgroup>
<thead>
<tr>
<th>ID</th>
<th>Principle</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>HP-DR-01</td>
<td>Disaster Recovery</td>
<td>Hệ thống BẮT BUỘC phải có cơ chế sao lưu (backup/snapshot) tự động
và định kỳ cho các dữ liệu quan trọng (VD: Qdrant cluster, Terraform
state). <strong>Việc triển khai nguyên tắc này phụ thuộc vào khả năng kỹ
thuật của hạ tầng; nếu tier dịch vụ không hỗ trợ, một giải pháp thay thế
phải được định nghĩa trong Luật (QD-LAW), hoặc ghi nhận là nợ kỹ
thuật.</strong></td>
</tr>
<tr>
<td>HP-DR-02</td>
<td>Data Sync</td>
<td>Dữ liệu vector và metadata (ví dụ trên Firestore) phải luôn được
đồng bộ. Mọi thao tác ghi phải đảm bảo tính nhất quán giữa các hệ
thống.</td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

**Điều VII – Quản lý Cursor**

<table>
<colgroup>
<col style="width: 6%" />
<col style="width: 19%" />
<col style="width: 73%" />
</colgroup>
<thead>
<tr>
<th>ID</th>
<th>Principle</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>HP-CS-01</td>
<td>Autonomous Execution</td>
<td>Execute to completion; stop only on blocking errors.</td>
</tr>
<tr>
<td>HP-CS-02</td>
<td>Mandatory Verification &amp; Fixes</td>
<td>Khi CI thất bại, Cursor được phép tự động sửa lỗi và thử lại tối đa
<strong>2 lần</strong>. Sau lần thứ 2 nếu vẫn thất bại, quy trình sẽ
dừng lại và thông báo cho Owner.</td>
</tr>
<tr>
<td>HP-CS-03</td>
<td>Rule Preservation</td>
<td>No delete/modify rules unless explicit prompt.</td>
</tr>
<tr>
<td>HP-CS-04</td>
<td>PR Description Autogeneration</td>
<td>Cursor prepend summary table to PR description.</td>
</tr>
<tr>
<td>HP-CS-05</td>
<td>Phân tách Quyền Ghi Secrets</td>
<td>• Các runner CI/CD thông thường (chạy test, build tại các repo con
như agent-data-test) <strong>bị cấm tuyệt đối</strong> quyền
secrets:write.&lt;br&gt;&lt;br&gt; • Chỉ duy nhất quy trình đồng bộ
secrets tự động (nếu có) mới được cấp quyền secrets:write để cập nhật
secrets.</td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

**Điều VIII – Phụ lục: Bảng Điều Kiện WIF Chuẩn Hóa**

Mục này quy định các điều kiện bắt buộc phải được cấu hình trong
Terraform (Policy as Code) để kiểm soát truy cập từ GitHub Actions, nhằm
ngăn chặn triệt để lỗi unauthorized\_client.

<table>
<colgroup>
<col style="width: 17%" />
<col style="width: 15%" />
<col style="width: 67%" />
</colgroup>
<thead>
<tr>
<th>Kịch bản</th>
<th>Repository</th>
<th>Điều kiện attributeCondition</th>
</tr>
</thead>
<tbody>
<tr>
<td>Pull Request (Môi trường Test)</td>
<td>agent-data-test</td>
<td>assertion.repository == 'Huyen1974/agent-data-test' &amp;&amp;
assertion.ref.startsWith('refs/heads/')</td>
</tr>
<tr>
<td>Release theo Tag (Test)</td>
<td>agent-data-test</td>
<td>assertion.repository == 'Huyen1974/agent-data-test' &amp;&amp;
assertion.ref.startsWith('refs/tags/')</td>
</tr>
<tr>
<td>Deploy (Môi trường Production)</td>
<td>agent-data-production</td>
<td>assertion.repository == 'Huyen1974/agent-data-production' &amp;&amp;
assertion.ref == 'refs/heads/main'</td>
</tr>
<tr>
<td><strong>Release Production theo Tag</strong></td>
<td><strong>agent-data-production</strong></td>
<td><strong>assertion.repository == 'Huyen1974/agent-data-production'
&amp;&amp; assertion.ref.startsWith('refs/tags/')</strong></td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

## **Ghi chú:** Provider cũ github-provider (với alias cursor-ci-provider) sẽ được giữ lại trong 30 ngày kể từ ngày cập nhật để đảm bảo các quy trình cũ không bị gián đoạn trong quá trình chuyển đổi. **Sau thời gian này, alias phải được xóa bỏ.**  Phụ lục – Khung 5 Luật Chuyên đề

1.  **GC-LAW** (Google Cloud)

2.  **TF-LAW** (Terraform)

3.  **GH-LAW** (GitHub)

4.  **QD-LAW** (Qdrant)

5.  **CS-LAW** (Cursor)
