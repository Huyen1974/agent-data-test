**📜 File Quy tắc Dự án: RULES_agent-data-langroid.md (Version 1.2)**

**Cập nhật:** August 07, 2025 (Phiên bản tuân thủ Hiến pháp v1.11e và các Luật liên quan)

**⛔ QUY TẮC CURSOR - DỰ ÁN AGENT DATA LANGROID (Bản Hoàn Chỉnh)**

*Tài liệu này là nguồn chân lý duy nhất cho mọi hoạt động của bạn. Mọi hành động phải tuân thủ nghiêm ngặt các quy tắc dưới đây.*

**1. Bối cảnh & Phạm vi Vận hành**

Bạn chỉ làm việc trong các bối cảnh đã được định nghĩa dưới đây.

- **Đường dẫn Dự án Duy nhất:**

- /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid

- **Project Google Cloud Duy nhất:**

- github-chatgpt-ggcloud

- **Service Account Duy nhất:**

- chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com

- **Các Repository trong Phạm vi:**

- agent-data-test (Repo phát triển & kiểm thử)

- agent-data-production (Repo sản phẩm)

- chatgpt-githubnew (Repo trung tâm quản lý secrets)

- **Kiểm tra nhanh WIF:** Trước khi đẩy các thay đổi liên quan đến quyền hạn, bạn nên chạy lệnh sau trên máy cục bộ để mô phỏng và kiểm tra các điều kiện WIF: gcloud auth application-default login --impersonate-service-account=\$GCP_SERVICE_ACCOUNT

**2. Quy tắc Quản lý Hạ tầng (Terraform)**

**2.1 Quy ước đặt tên Bucket**

- Mọi bucket do Terraform quản lý hoặc khởi tạo mới **BẮT BUỘC** tuân thủ định dạng:

> \<standard-prefix\>-agent-data-\<purpose\>-\<env\>

- **standard-prefix**: cố định là huyen1974.

- **Ký tự**: bắt buộc dùng dấu gạch ngang (-), **cấm tuyệt đối** dấu gạch dưới (\_).

- **purpose**: mô tả mục đích bucket (ví dụ: tfstate, artifacts, backup).

- **env**: môi trường áp dụng (dev, test, prod).

**
2.2 Danh sách bucket cụ thể**

| Tên Bucket | Mục đích (\<purpose\>) | Môi trường (\<env\>) |
|----|----|----|
| huyen1974-agent-data-artifacts-test | artifacts | test |
| huyen1974-agent-data-artifacts-production | artifacts | production |
| huyen1974-agent-data-knowledge-test | knowledge | test |
| huyen1974-agent-data-knowledge-production | knowledge | production |
| huyen1974-agent-data-logs-test | logs | test |
| huyen1974-agent-data-logs-production | logs | production |
| huyen1974-agent-data-qdrant-snapshots-test | qdrant-snapshots | test |
| huyen1974-agent-data-qdrant-snapshots-production | qdrant-snapshots | production |
| huyen1974-agent-data-source-test | source | test |
| huyen1974-agent-data-source-production | source | production |
| huyen1974-agent-data-tfstate-test | tfstate | test |
| huyen1974-agent-data-tfstate-production | tfstate | production |
| huyen1974-agent-data-backup-test | backup | test |
| huyen1974-agent-data-backup-production | backup | production |

**
2.3 Quy định về bảo mật & truy cập**

- **Uniform Bucket-Level Access (UBLA)**: tất cả bucket mới **BẮT BUỘC** bật UBLA để tuân thủ **Hiến pháp (HP-02)** và **TF-LAW (§4.3)**.

- **Legacy bucket**: các bucket được tạo trước khi Hiến pháp có hiệu lực nhưng chưa bật UBLA được xếp loại “legacy” và sẽ được xử lý theo nợ kỹ thuật **TD-TF-01**.

**2.4 Lưu ý về cập nhật & bảo trì**

- Khi bổ sung hoặc thay đổi bucket, **bắt buộc** cập nhật bảng danh sách ở mục 2.2 để đảm bảo Terraform state và tài liệu luôn đồng bộ.

- Mọi thay đổi liên quan đến bucket phải được commit kèm lý do và liên kết tới issue hoặc ticket kỹ thuật liên quan.

**3. Quản lý Artifacts & Docker Images**

- **Nơi lưu trữ:** Mọi Docker images, Cloud Functions và các artifact khác phải được lưu trữ trên **Google Artifact Registry**.

- **Phân tách môi trường:** Sẽ có các repository riêng biệt trong Artifact Registry cho mỗi môi trường: agent-data-test và agent-data-production .

- **Chính sách Lưu giữ (Retention):** Việc lưu giữ artifact BẮT BUỘC phải tuân thủ quy trình 2 giai đoạn:

- **14 ngày:** Các artifact sẽ được tự động đánh dấu là "stale" (cũ) để cảnh báo sớm.

- **30 ngày:** Một quy trình tự động sẽ tạo GitHub Issue \[CLEANUP\] để yêu cầu phê duyệt dọn dẹp. Việc xóa bỏ chỉ được thực hiện thủ công sau khi Issue được đóng lại.

- Báo cáo và Cảnh báo: Một báo cáo tự động hàng tuần qua Slack sẽ tổng hợp số lượng artifact đang được đánh dấu "stale". Báo cáo này BẮT BUỘC phải được cấu hình với một ngưỡng cảnh báo (ví dụ: stale_count \< 5) và sẽ gửi một cảnh báo đặc biệt nếu số lượng vượt ngưỡng này.

### **4. Quản lý Dữ liệu (Firestore & Metadata) 4.1. Quy tắc Quản lý Qdrant**

- **Tên Cluster:** Cluster bạn làm việc có tên là agent-data-vector-dev-useast4.

- **Tên Collection:** Tên collection BẮT BUỘC phải theo định dạng \<env\>\_documents (ví dụ: test_documents, production_documents).

- **Vận Quản lý Trạng thái Cluster:** Mọi tác vụ vận hành (ví dụ: tạm dừng cluster để tiết kiệm chi phí) BẮT BUỘC phải được thực hiện thông qua Cloud Function manage_qdrant. Cụ thể, khi cần tạm dừng cluster, bạn phải gọi đến action stop, vì action này đã bao gồm bước tạo snapshot an toàn theo yêu_cầu của **QD-LAW §4.2**.

<!-- -->

- **Vai trò của Firestore:** Firestore được sử dụng cho hai mục đích chính:

1.  Lưu trữ

> **Session Memory** cho Agent.

2.  Lưu trữ

> **Metadata** cho các vector trong Qdrant.

- **Nguyên tắc Đồng bộ Bất biến:** Mọi thao tác ghi hoặc cập nhật vector vào Qdrant BẮT BUỘC phải được thực hiện song song với việc ghi hoặc cập nhật metadata tương ứng vào Firestore .

- Trong trường-hợp quy trình đồng bộ này gặp lỗi, hệ thống phải có cơ chế gửi cảnh báo ngay lập tức cho Owner (ví dụ: qua Slack) để xử lý thủ công.

- **Cấu trúc Metadata:** Cấu trúc chi tiết của metadata và các nhãn sẽ được định nghĩa trong các tài liệu thiết kế chuyên sâu. Nhiệm vụ của bạn là tuân thủ các cấu trúc đã được định nghĩa trong mã nguồn (ví dụ: Pydantic models).

- **Chính sách Skip Hợp lệ:** Trong trường hợp cluster Qdrant được tạm dừng (trạng thái SUSPENDED), các job CI/CD phụ thuộc vào Qdrant được phép bỏ qua (skip). Ngoại lệ này chỉ hợp lệ nếu Pull Request **KHÔNG** chứa thay đổi trong các đường dẫn file "liên quan đến Qdrant" (tham chiếu GLOBAL RULES - mục 2.3). Trước khi thực thi các tác vụ yêu cầu Qdrant, Owner phải có trách nhiệm kích hoạt lại cluster.

### **5. Quy tắc CI/CD & GitHub**

**5.1 Kiểm soát Lockfile**

- Lockfile (requirements.txt) **BẮT BUỘC** được tạo bằng:

> pip-compile --no-upgrade

- CI sẽ kiểm tra bằng:

> git diff --exit-code requirements.txt
>
> để đảm bảo file không bị chỉnh sửa thủ công.

**5.2 Pre-commit Hooks**

- Mọi commit **BẮT BUỘC** phải vượt qua các hook đã được định nghĩa trong .pre-commit-config.yaml, bao gồm:

- black, ruff, trufflehog, manifest-drift.

**5.3 Quy định về Workflow Tổng hợp (Pass Gate)**

- Repository chỉ được phép có duy nhất một workflow được trigger trực tiếp là: .github/workflows/pass-gate.yml

- Các workflow khác (lint-only.yml, terraform-plan.yml, secret-scan.yml, manifest-drift.yml, agent-e2e.yml) **BẮT BUỘC** phải được cấu hình với on: workflow_call và chỉ được kích hoạt bởi pass-gate.yml.

- Các workflow được gọi qua on: workflow_call **CẤM TUYỆT ĐỐI** sử dụng secrets: inherit. Workflow pass-gate.yml chỉ được phép truyền các giá trị đầu vào (inputs) hoặc biến môi trường (env) tối thiểu cần thiết, và không được truyền secrets cho các job được kích hoạt bởi PR từ fork.

**5.4 Branch Protection & Status Check**

- Chỉ thiết lập duy nhất 1 status check Required: **Pass Gate**

- Không để nhiều check riêng lẻ nhằm tránh đánh giá sai trạng thái tổng thể.

- **Ghi chú:** Tên status check "Pass Gate" là cố định. Mọi thay đổi đối với tên job hoặc context trong workflow pass-gate.yml **BẮT BUỘC** phải được cập nhật đồng bộ trong cài đặt Branch Protection để tránh tình trạng merge bị chặn hoặc "xanh giả".

**5.5 Chi tiết Job Gate** và Xử lý ngữ cảnh

- Job tổng hợp trong pass-gate.yml **PHẢI** chạy với điều kiện: if: \${{ always() }}.

<!-- -->

- **Khái niệm REQUIRED_JOBS:** Một danh sách các job con bắt buộc phải thành công được xác định dựa trên ngữ cảnh của Pull Request:

- **PR từ nhánh nội bộ:** Yêu cầu tất cả các job chính (lint, secret-scan, manifest-drift, terraform-plan, agent-e2e).

- **PR từ fork:** Không yêu cầu các job cần secrets/WIF (terraform-plan, agent-e2e).

<!-- -->

- Job gate **PHẢI FAIL** nếu bất kỳ job nào trong danh sách REQUIRED_JOBS có conclusion khác success. Các job skipped không thuộc REQUIRED_JOBS (ví dụ: do PR từ fork) sẽ được bỏ qua.

- **Ghi chú triển khai:** Việc xác định PR từ fork trong workflow có thể được thực hiện bằng điều kiện sau: if: \${{ github.event.pull_request.head.repo.fork == true }}. Dựa vào điều kiện này, danh sách REQUIRED_JOBS sẽ được điều chỉnh để loại bỏ các job cần secrets/WIF.

**5.6 Cấu hình Concurrency và Quy tắc Xác minh**

- File pass-gate.yml **BẮT BUỘC** phải có đoạn sau để hủy các lần chạy CI cũ khi có commit mới, tránh lãng phí tài nguyên và tình trạng đua trạng thái:

> concurrency:
>
> group: pass-gate-\${{ github.ref }}
>
> cancel-in-progress: true

- **Ghi chú Quan trọng:** Do có thiết lập cancel-in-progress: true, có thể có nhiều CI run được tạo ra rồi bị hủy cho cùng một commit. Vì vậy, bạn **BẮT BUỘC** phải tuân thủ nguyên văn quy trình **Post-push CI Verification** (GLOBAL RULES - mục 2.1): tìm đúng RUN_ID của commit SHA cuối cùng và chỉ theo dõi run đó để tránh đọc nhầm kết quả từ một run đã bị hủy.

**5.7 Terraform Init Chuẩn**

- Trong job plan:

> terraform init -reconfigure -backend-config=terraform/backend.hcl

- Trong job lint-only:

> terraform init -backend=false && terraform validate -no-color

- Cấm mọi backend auto để tránh lỗi “bucket not set”.

**5.8 Quy tắc về Shell an toàn & continue-on-error**

- Tuân thủ nguyên văn **GLOBAL RULES - mục 2.2**. Cấm tuyệt đối continue-on-error (ngoại trừ bước “auth fallback” nếu có), bắt buộc sử dụng shell: bash -euo pipefail {0} cho tất cả các bước run:.

> **5.8.1 Policy Guard cho Trigger và Cấu hình Job**
>
> Workflow pass-gate.yml **BẮT BUỘC** phải có một job workflow-policy-guard chạy đầu tiên. Job này có các trách nhiệm sau:

- Sử dụng các công cụ như actionlint hoặc grep để kiểm tra và **làm thất bại (fail)** workflow nếu phát hiện bất kỳ file workflow nào khác (ngoài pass-gate.yml) có chứa trigger on: push hoặc on: pull_request.

- Kiểm tra và làm thất bại workflow nếu phát hiện bất kỳ job nào trong danh sách REQUIRED_JOBS (định nghĩa tại mục 5.5) có sử dụng các điều kiện paths:, paths-ignore:, hoặc if: có khả năng làm job đó bị bỏ qua (skip) một cách không hợp lệ.

- Kiểm tra và làm thất bại workflow nếu phát hiện bất kỳ job nào trong danh sách REQUIRED_JOBS có chứa continue-on-error: true (ngoại trừ các bước "auth fallback" đã được cho phép).

> **5.8.2 File backend.hcl Bắt buộc**
>
> Mã nguồn Terraform **BẮT BUỘC** phải có file terraform/backend.hcl được commit vào repository. File này định nghĩa cấu hình backend chuẩn và là nguồn chân lý duy nhất cho việc khởi tạo Terraform.
>
> **5.8.3 Khóa cứng Permissions của Workflow**
>
> Mọi workflow **BẮT BUỘC** phải được cấu hình với quyền hạn ở mức tối thiểu:
>
> permissions: { contents: read }
>
> Chỉ những job thực sự cần OIDC mới được cấp thêm id-token: write. Cấm tuyệt đối sử dụng pull_request_target trong các repo con.
>
> **5.9 Post-push CI Verification (Chuẩn hóa Log và Artifact)**
>
> Quy trình này tuân thủ nguyên văn GLOBAL RULES - mục 2.1, với các chi tiết kỹ thuật được làm rõ như sau:

- **Xác định Lỗi:** Sau mỗi lần push/PR, CI sẽ kiểm tra các run có headSha trùng với commit hiện tại. Nếu có run thất bại (failure, cancelled, timed_out), quy trình tự sửa lỗi sẽ được kích hoạt.

- **Lưu và Trình bày Log:**

- Khi một vòng sửa lỗi bắt đầu, log của job thất bại **BẮT BUỘC** phải được lưu vào một file theo định dạng: .ci/\${SHA}.autofix\<N\>.log (với N là 1 hoặc 2).

- File log này **BẮT BUỘC** phải được tải lên (upload) làm **artifact** của CI run đó.

- **CẤM TUYỆT ĐỐI** commit các file log vào repository. Thư mục .ci/ phải được thêm vào file .gitignore.

- **Quy trình Tự sửa lỗi (Auto-fix):**

- **Vòng 1:** Commit bản sửa lỗi với message bắt đầu bằng \[AUTOFIX-1\] \<root-cause\>.

- **Vòng 2:** Nếu vẫn thất bại, lặp lại quy trình với commit message \[AUTOFIX-2\] \<root-cause\>.

- Sau 2 vòng nếu vẫn thất bại, Cursor phải dừng lại và tạo issue với tiêu đề: 🛑 CI still failing after 2 auto-fixes. Nội dung issue phải đính kèm link đến CI run thất bại cuối cùng.

**5.10 Pass-gate Merge Policy**

- Pull Request **chỉ được merge** khi workflow pass-gate.yml **XANH HOÀN TOÀN**.

**5.11 Tag cho Production Release**

- Tag **PHẢI** theo định dạng:

> vX.Y.Z (ví dụ: v1.2.3)

**5.12 Cảnh báo Nợ Kỹ thuật (tạm thời)**

- Cho đến khi dashboard agent-data-ops hoàn thiện (HP-OBS-01), các CI chính **PHẢI in ra**:

> ::warning:: Giám sát chưa hoàn chỉnh - vui lòng theo dõi thủ công.

**5.13 Chuẩn hoá Múi giờ CI/CD (UTC)**

- Mọi kiểm tra CI/CD, xác thực trạng thái pass-gate, phân tích lịch sử push/pull request BẮT BUỘC phải được thực hiện theo chuẩn múi giờ UTC.

- Quy định này nhằm tránh sự sai lệch giữa thời gian ghi nhận của GitHub Actions runner và các lệnh kiểm tra bằng CLI như gh run view, gh run list.

- Nội dung kế thừa từ tài liệu chính thức: PLAN MERGE TO LAW 1.12 (Mục 4.1 và 4.2).

**6. Quản lý Secrets (CỰC KỲ QUAN TRỌNG)**

- **Nguồn Chân lý:** **Google Secret Manager** là nguồn duy nhất cho giá trị của secrets.

- **Cơ chế Đồng bộ:** Secrets trên GitHub được quản lý **TẬP TRUNG**. Một workflow

> sync-secrets.yml tại repo chatgpt-githubnew là quy trình **DUY NHẤT** được phép ghi (secrets:write) secrets lên các repo agent-data-test và agent-data-production .

- <span class="mark">**Nhiệm vụ của Cursor:** Bạn **KHÔNG ĐƯỢC PHÉP** tạo, sửa, hoặc xóa secrets trực tiếp trên agent-data-test hoặc agent-data-production.</span> Quy trình Xử lý Sự cố (Fallback)**:** Trong trường hợp workflow sync-secrets.yml gặp sự cố kéo dài (\>24h), việc cập nhật thủ công sẽ được thực hiện theo quy trình fallback đã quy định tại GH-LAW §5.5.

- **Danh sách Secrets:** Dưới đây là danh sách các secret bạn sẽ làm việc.

| Mục đích | Tên Secret trên GitHub | Ghi chú |
|----|----|----|
| GCP Project ID | GCP_PROJECT_ID | Giá trị: github-chatgpt-ggcloud |
| Deployer SA | GCP_SERVICE_ACCOUNT | Giá trị: chatgpt-deployer@... |
| WIF Provider | GCP_WIF_PROVIDER | projects/.../providers/github-provider |
| WIF Pool | GCP_WIF_POOL | projects/.../workloadIdentityPools/agent-data-pool |
| SA Fallback Key | GCP_SA_KEY_JSON | Dùng khi WIF lỗi |
| OpenAI Key | OPENAI_API_KEY | Secret cho runtime |
| Lark App Secret | LARK_APP_SECRET | Secret cho runtime |
| Qdrant Mgmt Key | QDRANT_CLOUD_MGMT_KEY | Key quản lý Qdrant Cloud |
| Qdrant Cluster Key | QDRANT_CLUSTER1_KEY | Key truy cập cluster |
| Qdrant Cluster ID | QDRANT_CLUSTER1_ID | ID của cluster |

- \*\*Chính sách Luân chuyển:\*\* Các secret quan trọng (ví dụ: QDRANT_CLUSTER1_KEY, OPENAI_API_KEY) phải được luân chuyển định kỳ: 90 ngày cho môi trường production và 120 ngày cho môi trường test.

- **Cảnh báo Luân chuyển:** Một workflow giám sát (secrets-audit.yml) BẮT BUỘC phải được thiết lập để chạy hàng ngày. Workflow này phải có khả năng gửi cảnh báo qua Slack khi một secret quan trọng còn **dưới 15 ngày** là đến hạn luân chuyển.

**7. Quản lý Truy cập (IAM)**

- **Các quyền được phép cấp cho Service Account (chatgpt-deployer@...):**

- roles/artifactregistry.writer

- roles/cloudfunctions.developer

- roles/run.admin

- roles/secretmanager.secretAccessor

- roles/storage.admin

- roles/iam.serviceAccountUser

- roles/viewer

- roles/logging.logWriter

- roles/serviceusage.serviceUsageAdmin

- **Các quyền bị cấm tuyệt đối:**

- roles/secretmanager.admin

- roles/iam.serviceAccountAdmin

- roles/cloudscheduler.admin

- roles/pubsub.publisher

**8. Quy tắc Vận hành & Tự sửa lỗi**

Tất cả quy tắc liên quan đến:

- Giới hạn retry khi CI thất bại

- Quy tắc commit message \[AUTOFIX-x\] kèm mô tả root-cause

- Kiểm soát số lượng test (Manifest Drift) và quy trình cập nhật test_manifest_baseline.txt

- Thời gian chờ tối thiểu giữa các lần retry

- Yêu cầu xác minh CI trước khi báo cáo DONE

- Việc bắt buộc chạy verify_setup.sh (nếu tồn tại trong repo)

- **Quy trình Cập nhật Baseline Hợp lệ:** Khi cần thay đổi (thêm/bớt) file test, Pull Request **BẮT BUỘC** phải có một commit riêng biệt với commit message bắt đầu bằng \[baseline-update\]. Commit này chỉ được chứa thay đổi của các file test và file test_manifest_baseline.txt. Workflow pass-gate sẽ kiểm tra và thất bại nếu số lượng test thay đổi mà không có commit tuân thủ quy trình này.

**→ Được áp dụng nguyên văn từ tài liệu “BNEW GLOBAL RULES CURSOR 1.2”, mục 2.1 và §8.**

Project Rules **không lặp lại chi tiết** để tránh sai lệch. Mọi thay đổi đối với các quy tắc này **phải được cập nhật tại Global Rules**, sau đó Project Rules sẽ mặc định kế thừa.

**9. Quy tắc Bảo vệ RULES**

- Bạn tuyệt đối không được xóa bất kỳ nội dung nào trong file RULES này nếu không được yêu cầu rõ ràng.
