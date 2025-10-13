# Claude Code Runbook (Stable, Non-destructive)

## OBJECTIVE
Run Claude Code CLI like Gemini CLI for this repo: analyze code, run safe shells, edit files with approval, work ONLY on feature branches, and produce verifiable results. Use Claude 3.5 Sonnet model.

## PRE-FLIGHT CHECKLIST (quick)
- `gh auth status` → Logged in
- `ssh -T git@github.com` → "Hi <user>!"
- `claude --version` → CLI installed and on PATH
- `test -x .agents/claude/start.sh` → start script is executable (else: `git update-index --chmod=+x .agents/claude/start.sh`)

## STARTUP (canonical, ổn định)
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source ~/.zshrc || true
./CLI.POSTBOOT.250.sh || true
export CLAUDE_CODE_MODEL="${CLAUDE_CODE_MODEL:-claude-3-5-sonnet-20241022}"
export CLAUDE_CODE_TOOLS="${CLAUDE_CODE_TOOLS:-read_file,write_file,run_shell_command,search_file_content}"
exec claude code --model "$CLAUDE_CODE_MODEL" --allowed-tools "$CLAUDE_CODE_TOOLS"
```

Start script tương đương (idempotent): `.agents/claude/start.sh` phải khớp 100% với lệnh dài trên.

## ENVIRONMENT
- Python tooling: venv 3.11.x (ví dụ `.cienv`); tránh PEP 668 lỗi cài global.
- Lint/format: `pre-commit run --all-files`.
- Bỏ qua local dev dirs: `.genkit/`, `.lintenv/`, `tools/ai/` (đảm bảo script không bị ignore).
- Đảm bảo thư mục **.agents/** KHÔNG bị ignore trong `.gitignore` (để runbook & start script được commit).

## CONSTRAINTS
- Chỉ làm việc trên feature branch; không commit trực tiếp lên `main`.
- Không sửa dotfiles hệ thống nếu chưa được duyệt.
- Không đổi lockfiles trừ khi nhiệm vụ yêu cầu rõ.
- Hỏi trước khi thao tác phá huỷ (rm -rf, force push…).
- Không chạy lệnh phá huỷ (rm -rf, force-push, reset --hard) nếu **không có phê duyệt rõ ràng** trong chat.
- Tuân thủ `.pre-commit-config.yaml`.

## ALLOWED TOOLS
- `read_file`, `write_file`, `run_shell_command`, `search_file_content`.
- Git/GitHub: cho phép status/commit/push trên feature branch; xin duyệt khi push/force-push.

## VERIFICATION / SMOKE TESTS

### One-shot:
```bash
claude --version
```
Kỳ vọng: in ra version number.

### Help:
```bash
claude code --help
```
Kỳ vọng: hiển thị usage information.

### Interactive header check:
```bash
.agents/claude/start.sh
```
Header phải có `claude-3-5-sonnet-20241022`; thoát sạch sau khi verify.

### Tool checks trong phiên:
- `git status` (run_shell_command)
- Tạo `/tmp/claude_write_test.txt` (write_file + cat)
- `search_file_content` trên chuỗi có thật
- `web_fetch https://example.com` (200)

## ERROR HANDLING
- **Authentication**: nếu prompt login, hoàn tất trong browser rồi tiếp tục; nếu treo, terminate và restart.
- **Network**: verify internet connection; retry failed operations.
- **Rate limiting**: respect quotas; implement exponential backoff.
- **Missing dependencies**: ensure claude CLI is installed and in PATH.

## NOTES (Cursor integration)
Nếu gặp extension prompts, có thể skip; CLI hoạt động độc lập.

## ROLLBACK / RESET
- Reset environment: `unset CLAUDE_CODE_*`
- Clear session: terminate claude processes
- Re-auth: `claude auth login` if needed

# 📜 Hiến Pháp Hạ Tầng Agent Data – Version 1.11e (Final Freeze)

Updated: August 04, 2025 Purpose: Supreme principles governing Agent Data Langroid. All Laws and plans MUST comply. Scope: agent-data-test / agent-data-production Changes from v1.11d:
- • v1.11e: Tinh chỉnh cuối cùng về mô hình secrets cho phù hợp với thực tế hạ tầng, ràng buộc định dạng của tiền tố bucket, và tự động hóa hoàn toàn quy trình dọn dẹp artifact sau khi được phê duyệt. Đây là bản đóng băng cuối cùng.

## Điều I – Phạm vi & Mục tiêu
| ID | Principle | Description | Source Documents / Notes |
| --- | --- | --- | --- |
| HP-01 | Single Owner Simplicity | Single owner manages infrastructure for minimal, observable configs. | HẠ TẦNG GOOGLE CLOUD.docx (reflects single project architecture) |
| HP-02 | Absolute IaC with Minimalism | All resources via Terraform; Terraform quản lý khai báo secret (metadata), giá trị cụ thể được inject thủ công / CI, không hard-code trong HCL. Tất cả các GCS Bucket được tạo mới BẮT BUỘC phải bật uniform_bucket_level_access. | HẠ TẦNG GOOGLE CLOUD.docx, QDRANT INFO & Requirement.docx |
| HP-03 | No False Reporting | No “PASS/Complete” unless conclusion == success verified by CI logs. | Plan checkpoint V7.docx, 0.6b1-fix9 |
| HP-04 | Automated Test Count Control | Hệ thống tự động kiểm soát sự thay đổi về số lượng bài kiểm tra. Mọi thay đổi (thêm/bớt test) phải được phản ánh một cách tường minh thông qua việc cập nhật file "manifest" (test_manifest_baseline.txt). CI sẽ tự động thất bại nếu phát hiện có sự thay đổi chưa được ghi nhận (Manifest Drift ≠ 0). | Plan checkpoint V7.docx (CP0.4), o3 gap, User chốt cuối |
| HP-05 | Central Secrets Inheritance | Mô hình quản lý secrets được chuẩn hóa là quản lý tập trung, sử dụng một repo trung tâm (ví dụ: chatgpt-githubnew) để điều phối việc đồng bộ secrets từ Google Secret Manager sang các repo con thông qua script. Khi hạ tầng được nâng cấp lên tài khoản GitHub Organization, mô hình sẽ chuyển sang sử dụng Organization-Level secrets. | HẠ TẦNG GOOGLE CLOUD.docx, o3 X-2, user decision, o3 edit<br>Trong trường hợp quy trình đồng bộ tự động gặp sự cố kéo dài (ví dụ: >24 giờ), Owner được phép cập nhật secret thủ công tại repo trung tâm, với điều kiện bắt buộc phải có bản ghi kiểm toán (audit log) chi tiết. |

HP-06	Kiến trúc Hướng Dịch vụ & Giao diện	Hệ thống phải được xây dựng dựa trên các dịch vụ (services) độc lập và cung cấp các lớp giao diện (interfaces) để tương tác. Dữ liệu gốc phải được tách biệt khỏi lớp hiển thị.<br><br> (Ví dụ: dữ liệu gốc dạng JSON được tách biệt khỏi giao diện web render ra HTML).
Hiến pháp hóa nguyên tắc "Dữ liệu là Nước" và kiến trúc microservices, đảm bảo tính linh hoạt và khả năng mở rộng ở cấp độ cao nhất.

HP-07	Tích hợp An toàn với Bên ngoài	Mọi hoạt động tích hợp với hệ thống của bên thứ ba phải được tiếp cận theo một lộ trình quản trị rủi ro theo giai đoạn, ưu tiên các luồng chỉ đọc (read-only) trước khi triển khai các luồng ghi (write).<br><br> (Một hệ thống được xem là có rủi ro cao khi API của nó không có các cam kết rõ ràng về độ ổn định, giới hạn truy cập, hoặc cơ chế xác thực phức tạp).
Đặt ra một nguyên tắc an toàn cốt lõi cho việc kết nối với các hệ thống bên ngoài (như Lark Base), tránh các rủi ro không lường trước ảnh hưởng đến toàn bộ hệ thống.

HP-08	Mục tiêu Vận hành là Bắt buộc	Mọi dịch vụ cốt lõi được triển khai BẮT BUỘC phải có các Mục tiêu Cấp độ Dịch vụ (SLOs) được định nghĩa, đo lường và cảnh báo.
Nâng tầm quan trọng của việc giám sát hiệu năng và độ tin cậy từ cấp độ Luật lên cấp độ Hiến pháp, đảm bảo mọi thành phần trong hệ sinh thái đều phải đáp ứng tiêu chuẩn vận hành.


## Điều II – Quy ước Định danh Chung
| Resource | Standard Naming | Example | Notes |
| --- | --- | --- | --- |
| GCP Project | github-chatgpt-ggcloud |  | Dùng chung cho cả test/prod theo quyết định cuối cùng. |
| Service Account | chatgpt-deployer@<project>.iam.gserviceaccount.com | chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com | Least privilege. Đây là Service Account duy nhất được sử dụng. Cấm tạo SA mới trừ khi có sự sửa đổi Hiến pháp. |
| WIF Pool | agent-data-pool |  | Single pool. |
| WIF Provider | github-provider |  | Attribute conditions per repo, có kế hoạch di dời provider cũ. |
| GCS Bucket | <standard-prefix>/agent-data-<purpose>-<env> | huyen1974-agent-data-artifacts-test | Tiền tố chuẩn hóa (<standard-prefix>) được định nghĩa và quản lý trong TF-LAW, với giá trị mặc định là huyen1974. Tiền tố này BẮT BUỘC phải tuân thủ định dạng tên miền DNS (RFC 1035). Ghi chú: <purpose> là mục đích sử dụng (ví dụ: artifacts, tfstate, backup); <env> là môi trường (test hoặc production). |
<br>
Nguyên tắc chung về định danh:
- • Tài nguyên công khai (Bucket, Repo, Project ID): Bắt buộc chỉ dùng dấu gạch ngang (-).
- • Tài nguyên nội bộ (Secret ID, Qdrant Collection): Được phép dùng cả gạch ngang (-) và gạch dưới (_).
<br>
Ngoại lệ: Các bucket do Google Cloud tự sinh (vd: gcf-v2-sources*, artifacts.*.appspot.com) không thuộc phạm vi của quy ước này.

| Qdrant Cluster | agent-data-vector-dev-useast4 |  | Shared cluster for development. |
| --- | --- | --- | --- |
| Qdrant Collection | <env>_documents | test_documents, production_documents | Phân tách trong cluster dùng chung. |
| GitHub Repos | agent-data-<env> | agent-data-test, agent-data-production |  |
| Secrets (GCP) | <purpose>_<env> | Qdrant_agent_data_N1D8R2vC0_5 | Nguồn gốc tại Secret Manager, tham chiếu từ nguồn tập trung. |

## Điều III – Chính sách Bảo mật & Quyền hạn
| ID | Principle | Description |
| --- | --- | --- |
| HP-SEC-01 | Least Privilege | Only necessary roles; prohibit admin roles. |
| HP-SEC-02 | Secret Rotation | Rotate keys every 90 days for production; 120 days for test. |
| HP-SEC-03 | Audit Logging | Enable Cloud Audit Logs for DATA_WRITE. |
| HP-SEC-04 | Secret Scanning | Zero findings via TruffleHog. |
Xuất sang Trang tính

## Điều IV – Kiểm soát CI/CD
| ID | Principle | Description |
| --- | --- | --- |
| HP-CI-01 | Mandatory Checks | Include lint-only, agent-e2e, terraform-plan, secret-scan; all must succeed. |
| HP-CI-02 | Pass Gate | Verify combined status before merge. |
| HP-CI-03 | Artifact Retention | Các artifact cũ phải được quản lý vòng đời theo quy trình 2 giai đoạn: |
| 1. | Sau 14 ngày: Các artifact sẽ được tự động đánh dấu là "stale" (cũ) để cảnh báo sớm. |  |
| 2. | Sau 30 ngày: Một quy trình tự động sẽ tạo GitHub Issue [CLEANUP]... để yêu cầu phê duyệt. Việc xóa bỏ sẽ được thực hiện thủ công bởi người có thẩm quyền sau khi Issue được đóng lại. |  |

| HP-CI-04 | No Continue-on-Error | Prohibit in test/lint/validate jobs, except for auth fallback. |
| --- | --- | --- |
| HP-CI-05 | Rollback & Fallback | Roadmap ≥ 0.7 BẮT BUỘC phải cung cấp cơ chế rollback tự động; trước thời điểm đó, việc rollback được phép thực hiện thủ công. |

## Điều V – Quản lý Chi phí & Giám sát
| ID | Principle | Description |
| --- | --- | --- |
| HP-COST-01 | Budget Alerts | Budget alerts phải được cấu hình ở các ngưỡng 50%/80%/100%. |
| HP-OBS-01 | Observability | Hệ thống BẮT BUỘC phải có dashboard giám sát các chỉ số vận hành cốt lõi (VD: độ trễ truy vấn, chi phí CI/CD). Chi tiết về chỉ số sẽ được quy định trong Luật. |

## Điều VI – Quản lý Dữ liệu & Phục hồi Thảm họa (DR)
| ID | Principle | Description |
| --- | --- | --- |
| HP-DR-01 | Disaster Recovery | Hệ thống BẮT BUỘC phải có cơ chế sao lưu (backup/snapshot) tự động và định kỳ cho các dữ liệu quan trọng (VD: Qdrant cluster, Terraform state). Việc triển khai nguyên tắc này phụ thuộc vào khả năng kỹ thuật của hạ tầng; nếu tier dịch vụ không hỗ trợ, một giải pháp thay thế phải được định nghĩa trong Luật (QD-LAW), hoặc ghi nhận là nợ kỹ thuật. |
| HP-DR-02 | Data Sync | Dữ liệu vector và metadata (ví dụ trên Firestore) phải luôn được đồng bộ. Mọi thao tác ghi phải đảm bảo tính nhất quán giữa các hệ thống. |

## Điều VII – Quản lý Cursor
| ID | Principle | Description |
| --- | --- | --- |
| HP-CS-01 | Autonomous Execution | Execute to completion; stop only on blocking errors. |
| HP-CS-02 | Mandatory Verification & Fixes | Khi CI thất bại, Cursor được phép tự động sửa lỗi và thử lại tối đa 2 lần. Sau lần thứ 2 nếu vẫn thất bại, quy trình sẽ dừng lại và thông báo cho Owner. |
| HP-CS-03 | Rule Preservation | No delete/modify rules unless explicit prompt. |
| HP-CS-04 | PR Description Autogeneration | Cursor prepend summary table to PR description. |
| HP-CS-05 | Phân tách Quyền Ghi Secrets | • Các runner CI/CD thông thường (chạy test, build tại các repo con như agent-data-test) bị cấm tuyệt đối quyền secrets:write.<br><br> • Chỉ duy nhất quy trình đồng bộ secrets tự động (nếu có) mới được cấp quyền secrets:write để cập nhật secrets. |

## Điều VIII – Phụ lục: Bảng Điều Kiện WIF Chuẩn Hóa
Mục này quy định các điều kiện bắt buộc phải được cấu hình trong Terraform (Policy as Code) để kiểm soát truy cập từ GitHub Actions, nhằm ngăn chặn triệt để lỗi unauthorized_client.
| Kịch bản | Repository | Điều kiện attributeCondition |
| --- | --- | --- |
| Pull Request (Môi trường Test) | agent-data-test | assertion.repository == 'Huyen1974/agent-data-test' && assertion.ref.startsWith('refs/heads/') |
| Release theo Tag (Test) | agent-data-test | assertion.repository == 'Huyen1974/agent-data-test' && assertion.ref.startsWith('refs/tags/') |
| Deploy (Môi trường Production) | agent-data-production | assertion.repository == 'Huyen1974/agent-data-production' && assertion.ref == 'refs/heads/main' |
| Release Production theo Tag | agent-data-production | assertion.repository == 'Huyen1974/agent-data-production' && assertion.ref.startsWith('refs/tags/') |
Ghi chú: Provider cũ github-provider (với alias cursor-ci-provider) sẽ được giữ lại trong 30 ngày kể từ ngày cập nhật để đảm bảo các quy trình cũ không bị gián đoạn trong quá trình chuyển đổi. Sau thời gian này, alias phải được xóa bỏ.

Phụ lục – Khung 5 Luật Chuyên đề
| 1. | TF-LAW (Terraform) |
| --- | --- |
| 2. | GC-LAW (Google Cloud) |
| 3. | GH-LAW (GitHub) |
| 4. | QD-LAW (Qdrant) |
| 5. | APP-LAW () |

# PHỤ LỤC B – NGUYÊN TẮC PHÂN TÁCH MÃ NGUỒN

**(Phụ lục này là một phần không thể tách rời của Hiến pháp và có hiệu lực từ ngày 19/09/2025)**

---

### **Điều 1: Mục đích và Hiệu lực**

1.1. **Mục đích:** Phụ lục này được ban hành để giải quyết mâu thuẫn giữa nguyên tắc **"Code nhẹ để hành quân xa"** và nhu cầu xây dựng một **"Hộp Công cụ" (Toolbox)** mạnh mẽ nhằm tăng hiệu suất phát triển. Nó chính thức hóa việc phân tách mã nguồn thành hai loại với các quy tắc áp dụng riêng biệt.

1.2. **Hiệu lực Ghi đè:** Các quy định tại Phụ lục này có **giá trị cao hơn** và đóng vai trò là một lăng kính diễn giải cho toàn bộ Hiến pháp và các bộ Luật liên quan. Trong trường hợp có mâu thuẫn, quy định tại đây sẽ được ưu tiên áp dụng.

### **Điều 2: Định nghĩa và Phân loại Mã nguồn**

Hệ thống mã nguồn của dự án được chính thức phân thành hai loại:

2.1. **Mã Nguồn Vận hành (Production Code):**
    * **Định nghĩa:** Là toàn bộ phần mã nguồn cốt lõi, được đóng gói và triển khai để tạo ra sản phẩm cuối cùng.
    * **Phạm vi:** Các thư mục `agent_data/`, `api-service/`, `app-service-project/` và các thư mục tương tự chứa logic nghiệp vụ chính.
    * **Nguyên tắc Áp dụng:** Mã nguồn này **BẮT BUỘC** phải tuân thủ nghiêm ngặt nguyên tắc **"Code nhẹ để hành quân xa"**.

2.2. **Mã Nguồn Hỗ trợ (Development & Tooling Code):**
    * **Định nghĩa:** Là toàn bộ mã nguồn, scripts, và các file cấu hình chỉ phục vụ cho quá trình phát triển, kiểm thử, và tự động hóa CI/CD.
    * **Phạm vi:** Các thư mục `tools/` (chứa Hộp Công cụ), `tests/`, `artifacts/`.
    * **Nguyên tắc Áp dụng:** Mã nguồn này **KHÔNG** bị ràng buộc bởi nguyên tắc "Code nhẹ" và được phép mở rộng để phục vụ mục tiêu tăng cường hiệu suất và độ tin cậy cho quy trình phát triển.

### **Điều 3: Cơ chế Thực thi Kỹ thuật**

Việc phân tách hai loại mã nguồn trên **BẮT BUỘC** phải được thực thi bằng các cơ chế kỹ thuật sau:

3.1. **Cấu trúc Thư mục:**
    * Một thư mục cấp cao tên là **`tools/`** **BẮT BUỘC** phải được sử dụng để chứa toàn bộ các công cụ trong "Hộp Công cụ".

3.2. **Tệp tin `.dockerignore`:**
    * File `.dockerignore` ở gốc của mỗi dịch vụ **BẮT BUỘC** phải được cấu hình để **LOẠI TRỪ** toàn bộ các thư mục chứa "Mã Nguồn Hỗ trợ" (ví dụ: `tools/`, `tests/`) ra khỏi quá trình xây dựng Docker image.
    * Cơ chế này đảm bảo sản phẩm cuối cùng được triển khai luôn "nhẹ" và chỉ chứa "Mã Nguồn Vận hành".

### **Điều 4: Tác động đến các Luật hiện hành**

4.1. **Phạm vi Áp dụng của các Luật:** Phụ lục này làm rõ rằng các nguyên tắc và quy định trong các bộ Luật con (TF-LAW, GC-LAW, GH-LAW, QD-LAW, APP-LAW) được áp dụng chủ yếu cho **"Mã Nguồn Vận hành"**.

4.2. **Miễn trừ Sửa đổi:** Việc ban hành Phụ lục này **KHÔNG yêu cầu sửa đổi trực tiếp** nội dung của các bộ Luật con hiện hành. Thay vào đó, nó cung cấp một khung diễn giải chung. Ví dụ:
    * **GH-LAW & HP-04 (Kiểm soát Test):** Cơ chế đếm và kiểm soát `test_manifest_baseline.txt` sẽ được cấu hình để chỉ theo dõi các thay đổi trong thư mục `tests/` mà không bị ảnh hưởng bởi việc thêm/bớt công cụ trong thư mục `tools/`.
    * **TF-LAW:** Các quy định về IaC vẫn áp dụng cho hạ tầng vận hành, không áp dụng cho các script công cụ.

# PHỤ LỤC C – QUY HOẠCH KIẾN TRÚC DỮ LIỆU HỖN HỢP (SQL & NOSQL)

**(Phụ lục này là một phần không thể tách rời của Hiến pháp và có hiệu lực kể từ ngày ban hành)**

---

### **Điều 1: Mục đích và Hiệu lực**

1.1. **Mục đích:** Phụ lục này được ban hành để chính thức hóa việc bổ sung **Google Cloud SQL** vào hệ sinh thái hạ tầng và định nghĩa **Kiến trúc Dữ liệu Hỗn hợp (Hybrid Data Model)** làm nguyên tắc cốt lõi trong việc lưu trữ và xử lý dữ liệu.

1.2. **Hiệu lực Ghi đè:** Các quy định tại Phụ lục này có **giá trị cao hơn** và đóng vai trò là một lăng kính diễn giải cho toàn bộ Hiến pháp và các bộ Luật liên quan.

### **Điều 2: Công nhận Dịch vụ Lưu trữ Cốt lõi**

2.1. **Google Cloud SQL** (với engine là PostgreSQL) được chính thức công nhận là một dịch vụ lưu trữ cốt lõi của hệ thống, bên cạnh các dịch vụ đã được phê duyệt trước đây (Firestore, Google Cloud Storage, Qdrant).

### **Điều 3: Nguyên tắc Kiến trúc Dữ liệu Hỗn hợp**

Hệ thống **BẮT BUỘC** phải tuân thủ mô hình kiến trúc dữ liệu hỗn hợp để tận dụng tối đa thế mạnh của từng loại cơ sở dữ liệu:

3.1. **Firestore (NoSQL):** Đóng vai trò là "Hệ thống Ghi nhận" (System of Record) cho:
    * **Siêu dữ liệu (metadata)** của mọi loại đối tượng.
    * **Trạng thái thời gian thực (real-time state)** cho các tương tác trên giao diện người dùng.
    * **Dữ liệu phi cấu trúc hoặc bán cấu trúc** (ví dụ: nội dung văn bản dạng JSON).

3.2. **Cloud SQL (SQL):** Đóng vai trò là "Hệ thống Ghi nhận" (System of Record) cho:
    * **Dữ liệu kinh doanh có cấu trúc chặt chẽ**.
    * Dữ liệu có **mối quan hệ phức tạp** và yêu cầu tính toàn vẹn tham chiếu (referential integrity).
    * Dữ liệu phục vụ cho các tác vụ **phân tích và báo cáo**.

3.3. **Agent Data (Lớp Liên kết):** Lớp ứng dụng API của Agent Data đóng vai trò là **"Lớp Liên kết Truy vấn" (Query Federation Layer)**. Agent phải có khả năng phân tích yêu cầu, truy vấn đồng thời cả hai CSDL, và tổng hợp kết quả để đưa ra câu trả lời hoàn chỉnh.

### **Điều 4: Tác động và Yêu cầu Cập nhật các Luật Liên quan**

Việc ban hành Phụ lục này yêu cầu các bộ Luật sau phải được cập nhật để phản ánh kiến trúc mới:

4.1. **GC-LAW (Luật về Google Cloud):**
    * **BẮT BUỘC** phải bổ sung một mục mới quy định các quy tắc vận hành cho Cloud SQL, bao gồm:
        * Quy ước đặt tên instance.
        * Chính sách sao lưu tối thiểu (tuân thủ **HP-DR-01**).
        * Cơ chế quản lý chi phí, khuyến khích áp dụng chính sách bật/tắt theo lịch trình cho các môi trường không phải production.

4.2. **APP-LAW (Luật về Lớp Ứng dụng):**
    * **BẮT BUỘC** phải bổ sung một quy định yêu cầu lớp ứng dụng (API Gateway) phải có khả năng tương tác an toàn với cả hai CSDL.
    * **BẮT BUỘC** phải quy định rõ "Quy trình Truy vấn Hỗn hợp" (Hybrid Search) là bắt buộc: **(1) Lọc bằng thuộc tính trên SQL trước, (2) sau đó mới thực hiện Tìm kiếm ngữ nghĩa trên tập dữ liệu đã được thu hẹp.**

### Điều 5: Nguyên tắc Phân tách Môi trường

5.1. Toàn bộ dữ liệu trên các hệ thống lưu trữ (bao gồm GCS, Qdrant, Firestore, và Cloud SQL) BẮT BUỘC phải tuân thủ nguyên tắc phân tách hoàn toàn giữa môi trường `test` và `production`.

5.2. Việc phân tách phải được thực thi bằng các quy ước định danh tài nguyên (ví dụ: tiền tố, hậu tố) đã được quy định chi tiết trong các bộ Luật liên quan.

============================ I. TF LAW ===============================
🛠️ TF-LAW (Luật về Terraform) – Version 1.5 (Final Freeze)
Dưới đây là phiên bản cuối cùng đã được cập nhật theo các quyết định trên.
Updated: August 05, 2025 Purpose: Quy định các quy tắc cụ thể cho việc vận hành Terraform trong dự án Agent Data Langroid, tuân thủ Hiến pháp v1.11e. Luật này đảm bảo việc quản lý hạ tầng bằng code (IaC) được thực hiện một cách tối giản, nhất quán và an toàn. Scope: Toàn bộ mã nguồn Terraform trong các repository agent-data-test và agent-data-production.
Changes from v1.4: Bổ sung các ghi chú làm rõ về biến môi trường và vai trò của Phụ lục B để tăng tính tường minh. Đây là bản đóng băng cuối cùng.

Bảng Ánh xạ tới Hiến pháp
| Mục của TF-LAW | Ánh xạ tới Nguyên tắc Hiến pháp |
| --- | --- |
| §1: Phạm vi Quản lý | HP-02 (IaC Tối thiểu) |
| §2: Cấu trúc Thư mục & Tiền tố | HP-II (Quy ước Định danh) |
| §3: Quản lý State từ xa | HP-II (Quy ước Định danh) |
| §4: Quy tắc Module & Vòng đời | HP-02 (IaC Tối thiểu) |
| §5: Quy trình CI/CD | HP-CI-01, HP-CI-04 (Kiểm soát CI/CD) |
| §6: Chất lượng Code | HP-02 (IaC Tối thiểu) |
| §7: Quản lý Secrets | HP-05 (Kế thừa Secrets Tập trung) |
| §8: Quản lý Phiên bản | HP-02 (IaC Tối thiểu) |
| §9: Di dời Hạ tầng cũ | HP-II (Quy ước Định danh) |
| §10: Phục hồi Thảm họa (DR) | HP-DR-01 (Disaster Recovery) |
| Phụ lục A: Nợ Kỹ thuật | HP-02 (IaC Tối thiểu) |
| Phụ lục B: Tài nguyên Quan trọng | HP-02 (IaC Tối thiểu) |
Xuất sang Trang tính

§1: Phạm vi Quản lý – IaC Tối thiểu 1.1. Terraform
CHỈ ĐƯỢC PHÉP quản lý các tài nguyên có vòng đời tĩnh .
1.2. Terraform
KHÔNG ĐƯỢC PHÉP quản lý các tài nguyên có tính chất động hoặc được điều khiển bởi ứng dụng .
§2: Cấu trúc Thư mục & Tiền tố Chuẩn hóa 2.1. Toàn bộ mã nguồn Terraform BẮT BUỘC phải được đặt trong thư mục
terraform/ ở gốc của mỗi repository .
2.2. Cấu trúc thư mục chuẩn được áp dụng như sau :
terraform/ ├── modules/ │ └── gcs_buckets.tf ├── main.tf ├── variables.tf ├── outputs.tf └── backend.tf Ghi chú: Cấu trúc trên là một khuyến nghị để đảm bảo tính nhất quán. Các dự án có quy mô nhỏ hơn có thể điều chỉnh cho phù hợp, ví dụ như đặt các file .tf ở thư mục gốc
terraform/ .
2.3. Tiền tố chuẩn hóa (standard-prefix): * Biến
standard_prefix BẮT BUỘC phải được khai báo trong variables.tf .
* Giá trị mặc định của biến này được thiết lập là
huyen1974 .
* Mọi giá trị của tiền tố BẮT BUỘC phải tuân thủ định dạng tên miền DNS (RFC 1035) như quy định tại Điều II của Hiến pháp.
§3: Quản lý State từ xa (Remote State) 3.1. Trạng thái của Terraform BẮT BUỘC phải được lưu trữ trên GCS Bucket .
3.2. Tên bucket chứa state phải tuân thủ định dạng:
<standard-prefix>-agent-data-tfstate-<env> .

Ghi chú: Giá trị tfstate trong tên bucket tương ứng với giá trị <purpose> trong quy ước đặt tên của Hiến pháp.
3.2.1. Ghi chú: Biến <env> dự kiến nhận các giá trị là test hoặc production để tách biệt state giữa các môi trường. 3.3. Bucket chứa state BẮT BUỘC phải được bật tính năng khóa đối tượng (Object Versioning) và được cấu hình
lifecycle { prevent_destroy = true } .
§4: Quy tắc Module & Vòng đời Tài nguyên 4.1. Các tài nguyên cùng loại nên được gom vào các file logic để dễ quản lý (ví dụ: tất cả
google_storage_bucket trong file gcs_buckets.tf) .
4.2. Các tài nguyên quan trọng (xem danh sách tại Phụ lục B) BẮT BUỘC phải có khối lệnh
lifecycle { prevent_destroy = true } .
4.3. Mọi tài nguyên
google_storage_bucket được tạo mới BẮT BUỘC phải bao gồm thuộc tính uniform_bucket_level_access = true trong mã nguồn .
§5: Quy trình CI/CD
5.1. Pull Request: Mọi Pull Request BẮT BUỘC phải chạy thành công job
terraform-plan .
* Job này chỉ thực hiện
plan, không apply .
* Job được phép trả về mã thoát
2 (phát hiện có thay đổi) mà không bị coi là thất bại .
* continue-on-error: true chỉ được phép sử dụng cho bước dự phòng xác thực (auth fallback) như quy định tại HP-CI-04 .
5.2. Nhánh
main: Việc apply các thay đổi chỉ được thực hiện trên nhánh main và BẮT BUỘC phải được kích hoạt thủ công hoặc thông qua một nhãn (label) đặc biệt, yêu cầu sự phê duyệt .
§6: Chất lượng Code (Lint & Format)
6.1. Mọi mã nguồn Terraform trước khi merge BẮT BUỘC phải được định dạng bằng
terraform fmt .
6.2. Một job
terraform-lint sử dụng tflint BẮT BUỘC phải được chạy và thành công trong quy trình CI .
§7: Quản lý Secrets
7.1. Terraform BẮT BUỘC phải sử dụng tài nguyên
google_secret_manager_secret để khai báo sự tồn tại của một secret (metadata) .
7.2. Terraform
BỊ CẤM TUYỆT ĐỐI quản lý phiên bản hay giá trị của secret (google_secret_manager_secret_version) .
7.3. Giá trị của secret sẽ được quản lý và đồng bộ bởi quy trình tập trung như đã quy định tại HP-05 của Hiến pháp.
§8: Quản lý Phiên bản
8.1. Phiên bản Terraform BẮT BUỘC phải được khóa ở required_version ~> 1.8 .
8.2. Phiên bản của Google Provider BẮT BUỘC phải được khóa ở phiên bản
~> 4.57.0 để đảm bảo sự ổn định và tương thích với các kế hoạch đã được phê duyệt . Mọi nâng cấp phiên bản lớn (major version) phải được thực hiện trong một Pull Request riêng và được kiểm thử cẩn thận.
§9: Di dời Hạ tầng cũ (Legacy Migration) 9.1. Các GCS Bucket cũ có chứa dấu gạch dưới (
_) phải được lên kế hoạch di dời sang tên mới tuân thủ Hiến pháp .
9.2. WIF Provider cũ (
cursor-ci-provider) sẽ được giữ lại dưới dạng alias trong 30 ngày kể từ ngày Hiến pháp có hiệu lực, sau đó phải được xóa bỏ .
§10: Phục hồi Thảm họa (Disaster Recovery) 10.1. Trạng thái của Terraform (
tfstate) BẮT BUỘC phải được sao lưu định kỳ .
10.2. Một GCS Bucket riêng cho việc sao lưu BẮT BUỘC phải được tạo với tên tuân thủ định dạng:
<standard-prefix>-agent-data-backup-<env> .

Ghi chú: Giá trị backup trong tên bucket tương ứng với giá trị <purpose> trong quy ước đặt tên của Hiến pháp.

Phụ lục A – Nợ Kỹ thuật (Technical Debt)
Danh sách các hạng mục chưa tuân thủ Hiến pháp và cần có lộ trình khắc phục.
| ID Nợ | Hạng mục | Mô tả | Deadline |
| --- | --- | --- | --- |
| TD-TF-01 | Uniform Bucket-Level Access (UBLA) | Các GCS Bucket cũ được tạo trước ngày Hiến pháp có hiệu lực và chưa bật UBLA phải được lên kế hoạch di dời hoặc cập nhật. | 31-12-2025 |
| TD-TF-02 | Workflow Sao lưu tfstate | Xây dựng một workflow tự động (cron job) để sao lưu định kỳ tệp tfstate từ bucket "tfstate" sang bucket "backup" theo đúng yêu cầu của GC-LAW. | 30-09-2025 |


Phụ lục B – Danh sách Tài nguyên Quan trọng
Ghi chú: Danh sách này là nguồn tham chiếu chính cho các tài nguyên quan trọng. Các bộ Luật khác (ví dụ: GC-LAW) nên đồng bộ hoặc tham chiếu đến danh sách này để đảm bảo tính nhất quán. <br>
Theo quy định tại §4.2, các tài nguyên được liệt kê dưới đây BẮT BUỘC phải có khối lệnh lifecycle { prevent_destroy = true } trong mã nguồn Terraform.
- • google_storage_bucket
- • google_secret_manager_secret
- • google_project_iam_member
- • google_artifact_registry_repository
- • google_service_account
============================ II. GC LAW ===============================
⛅ GC-LAW (Luật về Google Cloud) – Version 1.4 (Phiên bản Hoàn chỉnh Cuối cùng)
Updated: August 05, 2025 Purpose: Quy định các quy tắc cụ thể cho việc vận hành trên Google Cloud, tuân thủ Hiến pháp v1.11e. Scope: Toàn bộ tài nguyên trên Google Cloud Platform được quản lý bởi dự án Agent Data Langroid.
Changes from v1.3:
- • Cập nhật toàn bộ Luật để phản ánh mô hình 1 Project duy nhất và các quy tắc mới nhất từ Hiến pháp v1.11e.
- • Bổ sung lại các ví dụ, ghi chú chi tiết, và phần giải thích bối cảnh từ các phiên bản trước để tăng tính rõ ràng và đầy đủ.

Bảng Ánh xạ tới Hiến pháp
| Mục của GC-LAW | Ánh xạ tới Nguyên tắc Hiến pháp | Rationale (Lý do) |
| --- | --- | --- |
| §1: Cấu trúc Project | HP-01, HP-II | Chi tiết hóa mô hình 1 Project duy nhất đã được Hiến pháp phê duyệt. |
| §2: Quản lý Truy cập (IAM & WIF) | HP-III, Điều VIII | Chuẩn hóa các điều kiện WIF để ngăn lỗi xác thực, tuân thủ bảng điều kiện trong Hiến pháp. |
| §3: Quản lý Secrets | HP-05, HP-SEC-02 | Cụ thể hóa mô hình đồng bộ secrets từ Google Secret Manager theo đúng nguyên tắc của Hiến pháp. |
| §4: Quản lý Lưu trữ | HP-II, HP-CI-03, HP-DR-01 | Áp dụng quy ước đặt tên và vòng đời tài nguyên đã được chốt trong Hiến pháp. |
| §5: Chính sách Vùng | HP-II (Qdrant Cluster) | Quy định vùng hoạt động mặc định và các ngoại lệ đã được phê duyệt. |
| §6: Quản lý Chi phí & Giám sát | HP-OBS-01, HP-COST-01 | Cụ thể hóa các yêu cầu về giám sát và kiểm soát chi phí. |
| §7: Phục hồi Thảm họa (DR) | HP-DR-01 | Chi tiết hóa các yêu cầu tối thiểu về tần suất và đích đến của bản sao lưu. |
| §8: Bài học Kinh nghiệm | HP-III, HP-IV | Ghi lại bối cảnh và lý do ra đời của các quy tắc WIF để tránh lặp lại lỗi trong quá khứ. |
| Phụ lục A: Ranh giới Logic | HP-01, HP-II | Làm rõ cách phân tách môi trường Test/Prod trong cùng một Project. |
Xuất sang Trang tính

§1: Cấu trúc Project 1.1. Toàn bộ hạ tầng của dự án (bao gồm cả môi trường Test và Production) BẮT BUỘC phải được triển khai trên
một Project Google Cloud duy nhất.
1.2. Project ID được phê duyệt là:
github-chatgpt-ggcloud.
1.3. Service Account duy nhất được phê duyệt là:
chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com.
§2: Quản lý Truy cập (IAM & WIF)
2.1. Workload Identity Federation (WIF) là phương thức xác thực chính cho các quy trình CI/CD.
2.2. Bảng Điều kiện WIF Chuẩn hóa BẮT BUỘC phải được cấu hình trong Terraform và tuân thủ tuyệt đối bảng đã được phê duyệt trong Điều VIII của Hiến pháp v1.11e.
2.3. Hướng dẫn Triển khai và Di dời: * Terraform: Cấu hình BẮT BUỘC phải được quản lý bằng code. Ví dụ:
resource "google_iam_workload_identity_pool_provider" "github" { ... attribute_condition = "..." } .
* Di dời Provider cũ: Lệnh gcloud iam workload-identity-pools providers update-oidc... sẽ được sử dụng để di dời các provider cũ sang cấu hình chuẩn.
* Kiểm tra cục bộ:
- Trước khi đẩy lên CI, lập trình viên nên kiểm tra điều kiện WIF bằng lệnh gcloud auth application-default login --impersonate-service-account=[SA] để xác thực quyền.
- Xác thực Token: Để kiểm tra sâu hơn, có thể lấy và xác thực token bằng các lệnh tương tự như sau: gcloud sts get-token --audience="[AUDIENCE]"
§3: Quản lý Secrets
3.1. Nguồn Chân lý (Source of Truth): Google Secret Manager là nơi lưu trữ giá trị gốc và duy nhất của tất cả các secret.
3.2. Mô hình Đồng bộ: Việc đồng bộ secrets từ Google Secret Manager lên GitHub BẮT BUỘC phải tuân thủ mô hình đã quy định tại HP-05 của Hiến pháp v1.11e (sử dụng repo trung tâm và script đồng bộ cho tài khoản cá nhân).
3.3. Ví dụ Di dời Secret: gh secret set <SECRET_NAME> -b "<value>" --repo Huyen1974/chatgpt-githubnew.
§4: Quản lý Lưu trữ (GCS & Artifact Registry)

4.1. Quy ước Đặt tên Bucket: Mọi GCS Bucket BẮT BUỘC phải tuân thủ quy ước đặt tên <standard-prefix>-agent-data-<purpose>-<env> như đã quy định tại Điều II của Hiến pháp và được chi tiết hóa trong TF-LAW.
4.2. Vòng đời Artifact: Việc quản lý các artifact cũ (> 30 ngày) BẮT BUỘC phải tuân thủ quy trình đã quy định tại HP-CI-03 của Hiến pháp v1.11e (tạo GitHub Issue để phê duyệt và xóa thủ công).

4.3. Chính sách Truy cập Bucket: Mọi GCS Bucket được tạo mới BẮT BUỘC phải bật uniform_bucket_level_access = true, tuân thủ nguyên tắc HP-02 của Hiến pháp và được thực thi tại TF-LAW §4.3.
§5: Chính sách Vùng (Region Policy)
5.1. Vùng mặc định: asia-southeast1 (Singapore) được chỉ định là vùng mặc định cho tất cả các tài nguyên, trừ khi có ngoại lệ được ghi rõ. Cấu hình Terraform NÊN mã hóa cứng giá trị này trong file
tfvars cho các tài nguyên không phải Qdrant.
5.2. Ngoại lệ Qdrant: Cluster Qdrant được phép triển khai tại us-east4 cho đến khi có thông báo chính thức về việc hỗ trợ tại Singapore.
§6: Quản lý Chi phí & Giám sát
6.1. Cảnh báo Ngân sách: BẮT BUỘC phải được cấu hình theo nguyên tắc HP-COST-01.
6.2. Gán nhãn (Labeling): Mọi tài nguyên được tạo ra BẮT BUỘC phải được gán nhãn đầy đủ (project, environment, service) để phục vụ việc giám sát và kiểm soát chi phí.
6.3. Giám sát (Observability): Việc triển khai dashboard giám sát BẮT BUỘC phải tuân thủ nguyên tắc HP-OBS-01.
§7: Phục hồi Thảm họa (Disaster Recovery)
7.1. Nguyên tắc chung: Cơ chế sao lưu (backup/snapshot) tự động cho các dữ liệu quan trọng BẮT BUỘC phải được thiết lập theo nguyên tắc HP-DR-01 của Hiến pháp.
7.2. Tần suất Sao lưu Tối thiểu:
* Môi trường Production: Dữ liệu BẮT BUỘC phải được sao lưu tối thiểu 1 lần/ngày.
* Môi trường Test: Dữ liệu BẮT BUỘC phải được sao lưu tối thiểu 1 lần/tuần.
7.3. Đích đến của Bản sao lưu: * Tất cả các bản sao lưu BẮT BUỘC phải được lưu trữ trong GCS Bucket dành riêng cho việc sao lưu.
* Bucket này phải tuân thủ quy ước đặt tên đã được định nghĩa trong TF-LAW:
<standard-prefix>-agent-data-backup-<env>.
§8: Bài học Kinh nghiệm 8.1. Các quy tắc WIF trong §2 được tạo ra để khắc phục triệt để lỗi unauthorized_client đã gây ra sự chậm trễ đáng kể trong quá khứ. Nguyên nhân gốc rễ là do điều kiện WIF cũ chỉ cho phép CI chạy trên nhánh main, làm thất bại tất cả các quy trình chạy trên các nhánh feature hoặc Pull Request. Việc chuẩn hóa điều kiện cho phép refs/heads/ là bắt buộc để đảm bảo CI hoạt động thông suốt.

### §9: Quản lý Dịch vụ Firebase
9.1. **Các Dịch vụ được Phê duyệt:** Các dịch vụ Firebase sau được chính thức công nhận và cho phép sử dụng trong hệ sinh thái: **Firebase Hosting**, **Firebase Authentication**, và **Firestore**.
9.2. **Quy tắc Quản lý dưới dạng Mã nguồn (IaC):** Mọi cấu hình liên quan đến Firebase (bao gồm `firebase.json`, `firestore.rules`, và `firestore.indexes.json`) BẮT BUỘC phải được quản lý dưới dạng mã nguồn và lưu trữ trong repository.
9.3. **Tuân thủ Phân tách Môi trường:** Việc sử dụng Firestore BẮT BUỘC phải tuân thủ tuyệt đối **Điều 5** của **PHỤ LỤC C** trong Hiến pháp và các quy ước định danh đã được quy định tại **Phụ lục A** của Luật này.
9.4. **Ngoại lệ về Bucket:** Các GCS Bucket được Firebase Hosting tự động tạo ra và quản lý (ví dụ: bucket chứa nội dung trang web) được ghi nhận là tài nguyên do Google quản lý và không thuộc phạm vi của quy ước đặt tên tùy chỉnh trong **Điều II** của Hiến pháp.

Phụ lục A – Ranh giới Logic giữa Test và Production
Bảng này làm rõ cách các tài nguyên được phân tách một cách logic trong cùng một Project Google Cloud.

| Tài nguyên | Cách phân tách | Ví dụ |
| --- | --- | --- |
| GCS Bucket | Hậu tố -<env> | ...-artifacts-test vs. ...-artifacts-production |
| Artifact Registry | Tên repo riêng | .../agent-data-test vs. .../agent-data-production |
| Qdrant Collection | Tên collection riêng | test_documents vs. production_documents |
| Cloud Run Service | Tên service riêng | agent-data-test-service vs. agent-data-prod-service |
| **Firestore Collections** | Sử dụng tiền tố `<env>_` cho **TOÀN BỘ** tên collection. | `production_knowledge_documents`<br>`test_chat_sessions`<br>`production_customer_data` |
| **Cloud SQL Databases / Schemas** | Sử dụng database hoặc schema riêng biệt cho mỗi môi trường. | `main_db_production`<br>`main_db_test` |

============================ III. GH LAW ============================
🐙 GH-LAW (Luật về GitHub) – Version 1.3
Updated: August 05, 2025 Purpose: Quy định các quy tắc cụ thể cho việc vận hành trên GitHub trong dự án Agent Data Langroid, tuân thủ Hiến pháp v1.11e. Scope: Áp dụng cho các repository agent-data-test, agent-data-production, và repo trung tâm chatgpt-githubnew.
Changes from v1.2:
- • Bổ sung: Thêm quy trình báo cáo hàng tuần qua Slack cho các artifact cũ, nhằm tăng cường khả năng giám sát và tuân thủ Kế hoạch.

Bảng Ánh xạ tới Hiến pháp
| Mục của GH-LAW | Ánh xạ tới Nguyên tắc Hiến pháp | Rationale (Lý do) |
| --- | --- | --- |
| §1: Cấu trúc Repository | HP-01, HP-II | Chuẩn hóa cấu trúc các repository theo mô hình đã được phê duyệt. |
| §2: Quy tắc về Nhánh & Release | HP-IV, Điều VIII | Bảo vệ nhánh main và chuẩn hóa quy trình release để đảm bảo tính ổn định và tuân thủ WIF. |
| §3: Quy trình CI/CD | HP-CI-01, HP-CI-02 | Chi tiết hóa các workflow và các bước kiểm tra bắt buộc trong CI. |
| §4: Yêu cầu đối với Pull Request | HP-CS-04 | Chuẩn hóa quy trình review code và các quy ước để tăng chất lượng và tính rõ ràng. |
| §5: Quản lý Secrets | HP-05, HP-CS-05 | Cụ thể hóa mô hình kỹ thuật cho việc đồng bộ secrets, đảm bảo an toàn và tuân thủ Hiến pháp. |
| §6: Quy tắc Retry của Cursor | HP-CS-02 | Chi tiết hóa cơ chế tự sửa lỗi của Cursor. |
| §7: Quy trình Dọn dẹp Artifact | HP-CI-03 | Mô tả chi tiết workflow tạo và xử lý Issue dọn dẹp artifact. |
| §8: Bảo mật | HP-SEC-04 | Quy định các bước quét bảo mật và cơ chế bảo vệ mã nguồn. |

§1: Cấu trúc Repository 1.1. Các repository chính bao gồm
agent-data-test, agent-data-production, và repo trung tâm chatgpt-githubnew.
1.2. Cấu trúc thư mục trong mỗi repo BẮT BUỘC phải tuân thủ các quy ước đã định (ví dụ:
.github/workflows/, terraform/, .cursor/).
§2: Quy tắc về Nhánh & Release
2.1. Bảo vệ Nhánh main: Nhánh main BẮT BUỘC phải được bảo vệ với các quy tắc sau:
* Yêu cầu Pull Request (PR) để cập nhật.
* Yêu cầu tối thiểu 1 phê duyệt (approval).
* Bắt buộc tất cả các status check (context) được định nghĩa tại §3.2 phải thành công.
* Cấm force push.
2.2. Quy ước Định dạng Tag: Các tag được sử dụng cho việc "Release Production" BẮT BUỘC phải tuân thủ định dạng Semantic Versioning và có tiền tố v (ví dụ: v1.0.0, v1.2.3).
2.3. Quyền tạo Release Tag: Chỉ những người có quyền "Maintainer" hoặc cao hơn mới được phép tạo các tag release trên nhánh main.
§3: Quy trình CI/CD (Workflows)
3.1 GitHub CLI Auth Bootstrap (Cursor & Operators)
- •  Mục tiêu: chuẩn hoá xác thực gh cho Cursor/Operator trước khi chạy lệnh CI/CD thủ công (gh run, gh pr…).
- •  Nguồn token: Google Secret Manager secret: gh_pat_sync_secrets (Project: github-chatgpt-ggcloud). Token bắt buộc có scopes: repo, workflow.
- •  Công cụ: scripts/bootstrap_gh.sh (chế độ verify/apply).
- •  Quy tắc an toàn:
- • Không cấp secrets:write cho runner CI thường kỳ; chỉ quy trình đồng bộ secrets mới có thể có quyền này theo "Phân tách Quyền Ghi Secrets" (kế thừa luật hiện hành).
- • Script chỉ đọc PAT từ GSM và đăng nhập gh cục bộ, không ghi secrets lên GitHub.
- •  Cách dùng nhanh:
# Kiểm chứng token (không thay đổi cấu hình gh)
PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" scripts/bootstrap_gh.sh verify

# Đăng nhập gh (keyring) để chạy gh run/gh pr…
PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" scripts/bootstrap_gh.sh apply

# Kiểm tra:
gh auth status -h github.com
- •  Khi nào phải chạy:
- • Mỗi phiên thao tác mới, hoặc khi gặp lỗi gh "not authenticated".
- • Trước khi dùng các lệnh gh nằm trong quy trình GH-LAW §3 (CI/CD).

3.2. Quy định về Toolchain: Các workflow có sử dụng Terraform BẮT BUỘC phải có bước setup-terraform để cài đặt đúng phiên bản ~> 1.8 như đã quy định trong TF-LAW §8.
3.3. Các Status Check Bắt buộc (Pass-gate): Để một PR được phép merge vào nhánh main, các status check (context) sau BẮT BUỘC phải thành công (trạng thái xanh ✅):
* lint-only * terraform-plan * secret-scan * agent-e2e (hoặc các job test tương đương) * manifest-drift-check

§4: Yêu cầu đối với Pull Request (PR) 4.1.
Quy ước Tên nhánh: Tên nhánh BẮT BUỘC phải tuân thủ quy ước prefix/description (ví dụ: feat/add-new-tool, fix/bug-123).
4.2.
Mô tả PR: Mô tả của PR BẮT BUỘC phải chứa bảng tóm tắt tự động do Cursor tạo ra theo nguyên tắc HP-CS-04.
§5: Quản lý Secrets 5.1.
Mô hình Kỹ thuật: Việc đồng bộ secrets từ Google Secret Manager lên GitHub BẮT BUỘC phải được thực hiện thông qua một workflow sync-secrets.yml chạy tại repo trung tâm chatgpt-githubnew.
5.2.
Cơ chế Kích hoạt: Workflow sync-secrets.yml phải có 2 cơ chế kích hoạt:
* Chạy tự động theo lịch (cron) tối thiểu 1 lần/ngày.
* Chạy thủ công (
workflow_dispatch) khi cần đồng bộ ngay lập tức.
5.3.
Cơ chế Xác thực: Workflow này BẮT BUỘC phải sử dụng một PAT (Personal Access Token) có đủ quyền hạn để ghi secrets (secrets:write) lên các repo con.
5.4.
Quyền hạn của Runner: Runner ở các repo con (agent-data-test, agent-data-production) BỊ CẤM TUYỆT ĐỐI quyền secrets:write, tuân thủ HP-CS-05.
5.5.
Quy trình Xử lý Sự cố (Fallback): Trong trường hợp quy trình đồng bộ tự động gặp sự cố kéo dài, việc cập nhật secret thủ công lên repo con được cho phép, nhưng BẮT BUỘC phải kèm theo một bản ghi kiểm toán (audit log) ghi rõ lý do, người thực hiện và thời gian.
§6: Quy tắc Retry và Tự sửa lỗi của Cursor 6.1. Khi CI thất bại, Cursor được phép tự động sửa lỗi và push lại cùng nhánh
tối đa 2 lần.
6.2. Sau lần retry thứ 2 nếu vẫn thất bại, quy trình BẮT BUỘC phải dừng lại và thông báo cho Owner.
6.3. Thời gian chờ (cool-down) giữa các lần retry sẽ được quy định chi tiết trong
CS-LAW.
§7: Quy trình Dọn dẹp và Giám sát Artifact 7.1. Giai đoạn 1 (Cảnh báo sớm): Một workflow tự động BẮT BUỘC phải chạy để đánh dấu các artifact cũ hơn 14 ngày là "stale". 7.2. Giai đoạn 2 (Yêu cầu Dọn dẹp): Một workflow tự động khác BẮT BUỘC phải được thiết lập để quét và tạo GitHub Issue [CLEANUP]... cho các artifact cũ hơn 30 ngày. 7.3. Cơ chế Xác thực: Các workflow này BẮT BUỘC phải sử dụng một PAT hoặc GitHub App có đủ quyền hạn cần thiết (ví dụ: issues:write). 7.4. Giám sát và Báo cáo: Một quy trình tự động BẮT BUỘC phải chạy hàng tuần để tổng hợp số lượng artifact đã được đánh dấu "stale" và gửi báo cáo qua Slack. Báo cáo này BẮT BUỘC phải có ngưỡng cảnh báo (ví dụ: stale_count < 5) và sẽ gửi cảnh báo nếu vượt ngưỡng, tuân thủ yêu cầu trong Plan V12. 7.5. Việc xóa artifact chỉ được thực hiện thủ công sau khi Issue tương ứng đã được phê duyệt và đóng lại.
§8: Bảo mật 8.1.
Quét Secret: Mọi Pull Request BẮT BUỘC phải chạy thành công job quét secret (ví dụ: TruffleHog).
8.2.
Bảo vệ Workflow: Thư mục .github/workflows/ BẮT BUỘC phải được bảo vệ bằng file CODEOWNERS để yêu cầu sự phê duyệt từ người có thẩm quyền trước khi thay đổi các quy trình CI/CD.

Phụ lục A – Nợ Kỹ thuật
| ID Nợ | Hạng mục | Mô tả | Deadline |
| --- | --- | --- | --- |
| TD-GH-01 | Chuyển sang Organization-Level Secrets | Khi hạ tầng được nâng cấp lên tài khoản GitHub Organization, mô hình đồng bộ secrets bằng script sẽ được thay thế bằng cơ chế secrets: inherit của GitHub. | 31-12-2025 |

============================ IV. QD LAW ============================

📦 QDRANT LAW (Luật về Qdrant) – Version 1.2
Updated: August 05, 2025 Purpose: Quy định các quy tắc cụ thể cho việc vận hành Qdrant trong dự án Agent Data Langroid, tuân thủ Hiến pháp v1.11e. Scope: Áp dụng cho Qdrant Cloud cluster, các collection, và các tài nguyên phụ trợ (ví dụ: Cloud Function manage_qdrant).
Changes from v1.1:
- • Làm rõ và bổ sung các yêu cầu kỹ thuật bắt buộc cho Cloud Function manage_qdrant, bao gồm biến môi trường, logging, và quy trình snapshot.
- • Cập nhật Phụ lục Nợ Kỹ thuật cho rõ ràng hơn.

Bảng Ánh xạ tới Hiến pháp
| Mục của QD-LAW | Ánh xạ tới Nguyên tắc Hiến pháp | Rationale (Lý do) |
| --- | --- | --- |
| §1: Cấu trúc Cluster | HP-II (Naming), HP-QD-03 (Shared Cluster) | Chuẩn hóa quy ước đặt tên và mô hình sử dụng cluster dùng chung. |
| §2: Quản lý Collection | HP-II (Collection Naming) | Quy định cách đặt tên để phân tách dữ liệu các môi trường. |
| §3: Đồng bộ Metadata | HP-DR-02 (Data Sync) | Bắt buộc phải có sự nhất quán giữa vector và metadata. |
| §4: Quản lý Vận hành | HP-02 (IaC Tối thiểu) | Định nghĩa các công cụ tự động hóa để quản lý trạng thái và chi phí của cluster. |
| §5: Quản lý Secrets | HP-05, HP-SEC-02 | Tuân thủ mô hình quản lý secrets tập trung và chính sách luân chuyển. |
| §6: Chính sách Vùng | HP-II (Qdrant Cluster) | Tuân thủ chính sách vùng và kế hoạch di dời đã được Hiến pháp phê duyệt. |
| §7: Phục hồi Thảm họa (DR) | HP-DR-01 | Chi tiết hóa các yêu cầu về sao lưu cho Qdrant, tuân thủ các Luật khác. |
Xuất sang Trang tính

§1: Cấu trúc Cluster 1.1.
Mô hình: Hệ thống BẮT BUỘC sử dụng mô hình cluster dùng chung (shared cluster) cho cả môi trường Test và Production.
1.2.
Quy ước Đặt tên: Tên của cluster BẮT BUỘC phải tuân thủ quy ước đã được phê duyệt trong Điều II của Hiến pháp (agent-data-vector-dev-useast4).
§2: Quản lý Collection 2.1.
Quy ước Đặt tên: Việc phân tách dữ liệu giữa các môi trường BẮT BUỘC phải được thực hiện bằng cách sử dụng các collection riêng biệt, với tên tuân thủ định dạng <env>_documents.
2.2.
Ví dụ: test_documents cho môi trường Test, production_documents cho môi trường Production.
§3: Đồng bộ Metadata 3.1. Mọi thao tác ghi hoặc cập nhật vector vào Qdrant BẮT BUỘC phải được thực hiện song song với việc ghi hoặc cập nhật metadata tương ứng vào Firestore, tuân thủ nguyên tắc HP-DR-02.
3.2. Trong trường hợp quy trình đồng bộ gặp lỗi, hệ thống phải gửi cảnh báo và cho phép thực hiện fallback thủ công kèm theo bản ghi kiểm toán.
§4: Quản lý Vận hành (Cloud Function) 4.1. Một Cloud Function tên là
manage_qdrant BẮT BUỘC phải được triển khai để quản lý trạng thái vận hành của Qdrant cluster.
4.2. Function này BẮT BUỘC phải cung cấp các giao diện (action) tối thiểu sau: * start (để kích hoạt lại cluster) * stop (BẮT BUỘC phải tạo snapshot trước khi tạm dừng cluster) * status (để kiểm tra trạng thái) * touch (để làm mới bộ đếm thời gian không hoạt động) 4.3.
Cấu hình Scheduler: Một Cloud Scheduler BẮT BUỘC phải được cấu hình để gọi đến action touch của function này một cách định kỳ (khuyến nghị: mỗi 10 phút) nhằm ngăn chặn việc cluster tự động tạm dừng.
4.4. Quyền Thực thi: Service Account được sử dụng bởi Cloud Scheduler BẮT BUỘC phải được cấp quyền roles/cloudfunctions.invoker để có thể kích hoạt Cloud Function. 4.5. Biến môi trường: Function BẮT BUỘC phải được cấu hình với các biến môi trường cần thiết, tối thiểu bao gồm: PROJECT_ID, QDRANT_CLUSTER_ID, QDRANT_API_KEY. 4.6. Logging: Function BẮT BUỘC phải sử dụng cơ chế ghi log có cấu trúc (Structured Logging) để phục vụ việc giám sát và gỡ lỗi.
§5: Quản lý Secrets 5.1. Các secret của Qdrant (API key, management key) BẮT BUỘC phải được quản lý theo mô hình tập trung đã được định nghĩa tại HP-05 của Hiến pháp và chi tiết hóa trong GH-LAW §5.
5.2. Việc luân chuyển (rotation) các secret này BẮT BUỘC phải tuân thủ chính sách đã định tại HP-SEC-02 (90 ngày cho production, 120 ngày cho test).
§6: Chính sách Vùng 6.1. Qdrant cluster BẮT BUỘC phải được triển khai tại vùng
us-east4 theo đúng ngoại lệ đã được phê duyệt trong Hiến pháp và GC-LAW §5 .
6.2. Một kế hoạch di dời (migration) sang vùng
asia-southeast1 phải được chuẩn bị và sẵn sàng thực thi khi Qdrant Cloud chính thức hỗ trợ .
§7: Phục hồi Thảm họa (DR) & Sao lưu 7.1. Cơ chế sao lưu tự động (snapshot) BẮT BUỘC phải được thiết lập theo nguyên tắc HP-DR-01 và các ghi chú về sự phụ thuộc vào bậc dịch vụ (tier).
7.2.
Tần suất sao lưu BẮT BUỘC phải tuân thủ quy định tối thiểu trong GC-LAW §7.2: hàng ngày cho production, hàng tuần cho test.
7.3.
Đích đến của bản sao lưu BẮT BUỘC phải là GCS Bucket chuyên dụng, tuân thủ quy ước đặt tên đã định trong TF-LAW §10.2 (...-backup-<env>).

Phụ lục A – Nợ Kỹ thuật
| ID Nợ | Hạng mục | Mô tả | Deadline |
| --- | --- | --- | --- |

============================ V. APP LAW ============================

# 🔵 APP-LAW (Luật về Lớp Ứng dụng) – Version 3.0 (Final Freeze)

**Updated:** September 10, 2025
**Purpose:** Quy định các quy tắc cụ thể cho việc phát triển, vận hành, và bảo mật lớp ứng dụng (Application Layer) của Hệ sinh thái Tri thức Động, tuân thủ Hiến pháp v1.11e và Quy hoạch Kiến trúc v6.0.
**Scope:** Toàn bộ mã nguồn ứng dụng (UI, API), các Core Services, và các quy trình tích hợp hệ thống bên ngoài.
**Changes from v2.0:** Phiên bản đóng băng cuối cùng. Siết chặt các quy tắc thực thi về SLOs, Lark Sync, RBAC, CI Gates và chính sách dữ liệu để sẵn sàng cho giai đoạn triển khai.

### Bảng Ánh xạ tới Hiến pháp
| Mục của APP-LAW | Ánh xạ tới Nguyên tắc Hiến pháp |
| :--- | :--- |
| §1: Hợp đồng API | HP-02 (IaC Tối thiểu), HP-OBS-01 (Observability) |
| §2: Lớp Giao diện | HP-II (Quy ước Định danh) |
| §3: Dịch vụ & Quy trình | HP-01 (Simplicity), HP-DR-02 (Data Sync) |
| §4: Dữ liệu & Sự kiện | HP-DR-02 (Data Sync) |
| §5: Tích hợp Hệ thống Ngoài| HP-DR-02 (Data Sync), HP-07 (Tích hợp An toàn) |
| §6: Vận hành & Release | HP-CI-05 (Rollback), HP-OBS-01 (Observability), HP-08 (SLOs Bắt buộc) |
| §7: Bảo mật Ứng dụng | HP-SEC-01 (Least Privilege), HP-SEC-03 (Audit Logging) |

### Nguyên tắc Ưu tiên
APP-LAW có thể định nghĩa các tiêu chuẩn và ngưỡng vận hành chặt chẽ hơn so với các quy định trong Hiến pháp hoặc các luật khác, nhưng không được phép nới lỏng các quy định đó. Trong trường hợp có xung đột, quy định chặt chẽ hơn sẽ được áp dụng (ví dụ: `APP-LAW` quy định Budget Alerts ở ngưỡng 70%/85%/100%, chặt hơn so với mức tối thiểu 50%/80%/100% của `Hiến pháp`).

---

### §1: Hợp đồng API (API Contract)
1.1. **Phiên bản (Versioning):** Tất cả các API công khai **BẮT BUỘC** phải có tiền tố phiên bản (ví dụ: `/api/v1/...`).
1.2. **Đặc tả (Specification):** Toàn bộ API **BẮT BUỘC** phải được định nghĩa bằng chuẩn OpenAPI 3.1. File đặc tả phải được lưu trong mã nguồn và được kiểm tra (lint) trong CI.
1.3. **Độ tin cậy (Reliability):**
    - Mọi request `POST`, `PUT`, `PATCH` **BẮT BUỘC** phải chứa header `Idempotency-Key`. Server phải trả về kết quả đã xử lý trước đó nếu nhận được key trùng lặp.
    - API **BẮT BUỘC** phải cung cấp các endpoint `/healthz` và `/readyz`.
1.4. **Cấu trúc Phản hồi (Response Envelope):** Các phản hồi lỗi **BẮT BUỘC** phải tuân thủ cấu trúc đã định nghĩa trong Phụ lục C của Quy hoạch v6.0.
1.5. **Giới hạn Truy cập (Rate Limiting & Pagination):**
    - API **BẮT BUỘC** phải trả về các header `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` để client có thể điều chỉnh hành vi.
    - Các endpoint trả về danh sách **BẮT BUỘC** phải hỗ trợ phân trang (pagination) theo cơ chế cursor hoặc offset.

### §2: Lớp Giao diện (Presentation Layer)
2.1. **Công nghệ:** Framework chính để phát triển giao diện người dùng được phê duyệt là **Vue.js** (phiên bản 3.5.x trở lên).
2.2. **Nguyên tắc Hiển thị:** Giao diện người dùng **BẮT BUỘC** phải tuân thủ nguyên tắc "Dữ liệu là Nước".
2.3. **Triển khai:** Giao diện người dùng sẽ được triển khai dưới dạng ứng dụng web tĩnh trên **Firebase Hosting**.

### §3: Dịch vụ Nền tảng & Quy trình (Core Services & Processes)
3.1. **Kiến trúc:** Hệ thống **BẮT BUỘC** phải được xây dựng dựa trên các Core Services có khả năng tái sử dụng.
3.2. **Xử lý Quy trình:** "Nhà Máy Quy trình" **BẮT BUỘC** phải hỗ trợ cả hai luồng quy trình Cố định và Bất định.
3.3. **Tương tác:** Mỗi bước trong quy trình phải có khả năng liên kết đến một "Trang con Làm việc".

### §4: Dữ liệu & Sự kiện (Data & Event)
4.1. **Định dạng Gốc:** Dữ liệu tri thức **BẮT BUỘC** phải được lưu trữ dưới dạng JSON có cấu trúc khối.
4.2. **Chuẩn hóa Sự kiện:** Mọi sự kiện qua Pub/Sub **BẮT BUỘC** phải tuân thủ **Event Schema v1**.
4.3. **Chính sách Xóa:** Mặc định áp dụng cơ chế **Xóa mềm (Soft Delete)**.
4.4. **Chính sách Dead-Letter Queue (DLQ):** Các sự kiện thất bại sau retry (tối đa 6 lần, exponential backoff) sẽ được chuyển vào DLQ và **BẮT BUỘC** phải có quy trình xử lý (redrive) thủ công.

### §5: Tích hợp Hệ thống Bên ngoài (External System Integration)
5.1. **Lộ trình Tích hợp:** Mọi hoạt động tích hợp với hệ thống có rủi ro cao (như Lark Base) **BẮT BUỘC** phải tuân thủ **lộ trình 3 giai đoạn** (Shadow Read → Dual-Write → Cutover).
5.2. **Giải quyết Xung đột:** Phải có một cơ chế giải quyết xung đột rõ ràng (ví dụ: Last-Writer-Wins) được định nghĩa trong ma trận.
5.3. **Ánh xạ Định danh:** **BẮT BUỘC** phải có một registry trung tâm để ánh xạ định danh (ID) giữa các hệ thống.
5.4. **Quy tắc Vận hành Tích hợp:** Dịch vụ Đồng bộ hóa (Sync Service) **BẮT BUỘC** phải:
    - Xác minh chữ ký của các webhook đến (nếu có).
    - Triển khai các cơ chế batching, exponential backoff, và throttling (token bucket) để tôn trọng giới hạn API của hệ thống ngoài.
    - Quản lý vòng đời token (refresh ~120 phút) và gửi cảnh báo khi thất bại.

### §6: Vận hành & Release (Operations & Release)
6.1. **Mục tiêu Vận hành (SLOs):** Hệ thống **BẮT BUỘC** phải được giám sát theo các chỉ số và mục tiêu sau:
    - **API Latency (P95):** < 600ms
    - **API Error Rate:** < 1%
    - **Sync-Lag (Lark→FS) P95:** ≤ 2 phút
    - **Sync DLQ Rate:** < 0.1% / ngày
6.2. **Chiến lược Release:** Chiến lược release mặc định là **Blue/Green**. Mọi thay đổi về cơ sở dữ liệu (index, rules) **BẮT BUỘC** phải được áp dụng trước khi chuyển traffic.
6.3. **Phục hồi Thảm họa (DR):** Các mục tiêu RPO/RTO (RPO ≤ 15 phút, RTO ≤ 30 phút) là yêu cầu bắt buộc.
6.4. **Cổng Kiểm soát CI (CI Gates):** Việc merge vào nhánh chính sẽ bị **CHẶN** nếu bất kỳ kiểm tra nào sau đây thất bại:
    - Linting OpenAPI 3.1.
    - Terraform plan cho rules và indexes không có thay đổi ngoài dự kiến ("plan sạch").
    - Unit test cho Firestore Rules.

### §7: Bảo mật Lớp Ứng dụng (Application-Layer Security)
7.1. **Phân quyền (RBAC):** Mọi truy cập vào dữ liệu và chức năng **BẮT BUỘC** phải được kiểm soát bởi mô hình RBAC (các vai trò: `owner`, `editor`, `viewer`, `agent`). Các quy tắc bảo mật của Firestore **BẮT BUỘC** phải có unit/integration test đi kèm.
7.2. **Xử lý Dữ liệu Nhạy cảm (PII):** Mọi log hệ thống **BẮT BUỘC** phải có cơ chế lọc (scrubbing).
7.3. **Chính sách Signed URL:** Việc cấp quyền truy cập vào file trên GCS **BẮT BUỘC** phải tuân thủ: phương thức là `GET-only`, TTL ≤ 15 phút, có mime whitelist, và chỉ áp dụng cho bucket đã được chỉ định.

### Phụ lục A – Nợ Kỹ thuật
| ID Nợ | Hạng mục | Mô tả | Deadline |
| :--- | :--- | :--- | :--- |
| TD-APP-01 | Tích hợp Lark Base | Hoàn thành Giai đoạn 1 (Shadow Read) và có báo cáo baseline về Sync SLOs. | TBD |
| TD-APP-02 | Công cụ DLQ/Redrive | Xây dựng công cụ và quy trình để xử lý các sự kiện trong Dead-Letter Queue. | TBD |
| TD-APP-03 | Unit Test cho Firestore Rules | Xây dựng bộ unit test cho các quy tắc bảo mật của Firestore. | TBD |

### Phụ lục B – Data Model & Indexes Tối thiểu
Để đảm bảo tính nhất quán, các collection sau được xem là tối thiểu và phải được định nghĩa trong Terraform:
- `knowledge_documents`
- `process_templates`
- `process_runs`
- `id_mapping_registry`
- **Ghi chú về Alias:** Cần đảm bảo tính nhất quán về tên gọi. Các tài liệu cũ có thể dùng tên `knowledge_nodes`, `process_traces`; từ nay sẽ được chuẩn hóa thành `knowledge_documents` và `process_runs`.
- Một danh sách các chỉ mục phức hợp (composite indexes) cần thiết cho các truy vấn chính phải được khai báo sớm.

### **Phụ lục B – Điều chỉnh Linh hoạt & Ngoại lệ Vận hành**

*(Phụ lục này được bổ sung nhằm ghi nhận các điều chỉnh quy trình vận hành theo yêu cầu của Owner để tối ưu hóa hiệu suất và tính tự động hóa, dựa trên các thực tiễn đã được chứng minh là hiệu quả.)*

---

#### **Điều GH-LAW-B1: Nguyên tắc Ưu tiên Chỉ đạo của Owner**

Các quy định trong Hiến pháp và các bộ Luật được thiết lập để đảm bảo sự ổn định và an toàn hệ thống. Tuy nhiên, khi Owner trực tiếp ra chỉ thị để giải quyết một ách tắc hoặc tối ưu hóa một quy trình, chỉ thị đó sẽ được ưu tiên. Mọi điều chỉnh mang tính lâu dài phát sinh từ chỉ thị này phải được văn bản hóa thành một điều khoản trong Phụ lục để đảm bảo tính minh bạch.

---

#### **Điều GH-LAW-B2: Ngoại lệ Phê duyệt cho nhánh `main` tại `agent-data-test`**

1.  **Bối cảnh:** Nhằm tái lập quy trình tự động hóa tối đa đã được vận hành hiệu quả trong các giai đoạn phát triển P1 đến P11.1, một ngoại lệ được áp dụng cho quy tắc "Yêu cầu tối thiểu 1 phê duyệt" được quy định tại **GH-LAW §2.1**.

2.  **Quy định Miễn trừ:**
    * **Phạm vi áp dụng:** Chỉ áp dụng cho repository `agent-data-test`.
    * **Nội dung:** Việc hợp nhất (merge) Pull Request vào nhánh `main` được phép diễn ra mà **không cần có bước phê duyệt (approval) thủ công** từ người dùng.

3.  **Điều kiện An toàn Bắt buộc Thay thế:**
    * Một Pull Request chỉ đủ điều kiện để được hợp nhất tự động vào nhánh `main` khi và chỉ khi **TẤT CẢ các status check bắt buộc (required status checks) được định nghĩa cho Pull Request đó đã chạy xong và có trạng thái thành công (xanh ✅)**.
    * Quy trình này trao quyền cho Agent (Codex) tự động hoàn tất vòng đời của một Pull Request ngay sau khi nó đã vượt qua toàn bộ các cổng kiểm soát chất lượng tự động.
