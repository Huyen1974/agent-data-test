# Comprehensive Infrastructure & CI/CD Information (Updated: March 26, 2025)

**Mục đích:** Cung cấp thông tin đầy đủ, chính xác và nhất quán về hạ tầng Google Cloud, quy trình CI/CD GitHub Actions, và môi trường phát triển local cho các AI/Agent hỗ trợ trong mọi khâu làm việc.

---

## I. Google Cloud Platform Infrastructure

### 1. Projects
* **Test Project:**
    * Project ID: `chatgpt-db-project` [cite: 1]
    * Project Number: `1042559846495` [cite: 1]
    * Region: `asia-southeast1` [cite: 1]
* **Production Project:**
    * Project ID: `github-chatgpt-ggcloud` [cite: 1]
    * Project Number: `812872501910` [cite: 1]
    * Region: `asia-southeast1` [cite: 1]

### 2. Service Accounts
* **Test:**
    * Email: `gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com` [cite: 1]
    * *Lưu ý:* Trong báo cáo CICD nhánh test, email được ghi là `gemini-service-account@github-chatgpt-ggcloud.iam.gserviceaccount.com`. Cần xác nhận lại email chính xác cho môi trường Test.
    * Roles: `roles/run.invoker`, `roles/cloudfunctions.invoker`, `roles/pubsub.publisher`, `roles/secretmanager.secretAccessor`, `roles/storage.objectAdmin`, `roles/cloudbuild.builds.builder`, `roles/workflows.editor`, `roles/workflows.invoker`, `roles/iam.serviceAccountTokenCreator`, `roles/iam.serviceAccountUser` [cite: 1]
* **Production:**
    * Email: `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com` [cite: 1]
    * Roles: `roles/run.invoker`, `roles/cloudfunctions.invoker`, `roles/pubsub.publisher`, `roles/secretmanager.secretAccessor`, `roles/storage.objectAdmin`, `roles/owner`, `roles/datastore.owner`, `roles/run.admin`, `roles/cloudfunctions.admin`, `roles/pubsub.admin`, `roles/cloudbuild.builds.builder`, `roles/workflows.editor`, `roles/workflows.invoker`, `roles/iam.serviceAccountTokenCreator`, `roles/iam.serviceAccountUser` [cite: 1]

### 3. Workload Identity Federation
* **Test:**
    * Pool ID: `github-test-pool` [cite: 1]
    * Provider ID: `github-test-provider` [cite: 1]
    * Full Name: `projects/1042559846495/locations/global/workloadIdentityPools/github-test-pool/providers/github-test-provider` [cite: 1]
* **Production:**
    * Pool ID: `github-pool` [cite: 1]
    * Provider ID: `github-provider` [cite: 1]
    * Full Name: `projects/812872501910/locations/global/workloadIdentityPools/github-pool/providers/github-provider` [cite: 1]

### 4. Buckets (Google Cloud Storage)
* **Test (`chatgpt-db-project`, Region: `asia-southeast1`):**
    * `huyen1974-my-terraform-test-state` (Terraform state) [cite: 1]
    * `huyen1974-artifact-storage-test` (Artifacts, delete after 30 days) [cite: 1]
    * `huyen1974-chatgpt-functions-test` (Functions/Containers source, abort incomplete uploads after 1 day) [cite: 1]
    * `huyen1974-log-storage-test` (Logs) [cite: 1]
    * `gcf-v2-sources-1042559846495-asia-southeast1` (Cloud Functions v2 artifacts, delete old versions after 3 versions) [cite: 1]
* **Production (`github-chatgpt-ggcloud`, Region: `asia-southeast1`):**
    * `huyen1974-my-terraform-state` (Terraform state) [cite: 1]
    * `huyen1974-artifact-storage` (Artifacts, delete after 30 days) [cite: 1]
    * `huyen1974-chatgpt-functions` (Functions/Containers source, abort incomplete uploads after 1 day) [cite: 1]
    * `huyen1974-log-storage` (Logs) [cite: 1]

### 5. Secrets (Stored in Google Secret Manager - `github-chatgpt-ggcloud`)
* **Secrets:** (All in `asia-southeast1`) [cite: 1]
    * `chatgpt-deployer-key` [cite: 1]
    * `chatgpt-deployer-service-account-json` [cite: 1]
    * `github-token-sg` [cite: 1]
    * `lark-access-token-sg` (Updated by `generate-lark-token` function) [cite: 1]
    * `lark-app-secret-sg` [cite: 1]
    * `openai-api-key-sg` [cite: 1]
* **Access:** Both service accounts (`gemini-service-account` và `chatgpt-deployer`) have `roles/secretmanager.secretAccessor`. [cite: 1]
* **Lưu ý:** Hiện tại secret của cả nhánh `main` và nhánh `test` đang dùng chung tại project Production (`github-chatgpt-ggcloud`). [cite: 1]

### 6. Docker (Artifact Registry)
* **Test Repository:** `asia-southeast1-docker.pkg.dev/chatgpt-db-project/gcf-artifacts` [cite: 1]
    * *Lưu ý:* Workflow CI/CD nhánh test đang push image vào `asia-southeast1-docker.pkg.dev/${{ secrets.PROJECT_ID }}/docker-repo/...`. Cần xác nhận lại tên repository chính xác (`gcf-artifacts` hay `docker-repo`).
* **Production Repository:** `asia-southeast1-docker.pkg.dev/github-chatgpt-ggcloud/docker-repo` [cite: 1]

### 7. Firestore
* **Test:**
    * Database Name: `test-default` [cite: 1]
    * Region: `asia-southeast1` [cite: 1]
* **Production:**
    * Database Name: `(default)` [cite: 1]
    * Region: `asia-southeast1` [cite: 1]

### 8. Cloud Functions
* **Test (Example):**
    * `dummy-function` (HTTP trigger, `asia-southeast1`) [cite: 1]
* **Production (Examples):**
    * `generate-lark-token` (HTTP trigger, `asia-southeast1`, updates `lark-access-token-sg`) [cite: 1, 2]
    * `lark_webhook` (HTTP trigger, `asia-southeast1`, xử lý webhook từ Lark) [cite: 2]
    * `check_lark_token` (HTTP trigger, `asia-southeast1`, kiểm tra tính hợp lệ của token Lark) [cite: 2]

### 9. Cloud Run
* Các container được build và deploy từ thư mục `containers/` thông qua CI/CD. [cite: 1]
* Ví dụ URL (Test): `https://deploytestfunctions-1042559846495.asia-southeast1.run.app` (Cần xác nhận đây là Cloud Run hay Function URL) [cite: 1]

### 10. Cloud Workflows
* Các workflow được định nghĩa trong file `.yaml` tại thư mục `workflows/` và deploy thông qua CI/CD. [cite: 1]

### 11. APIs Enabled
* `cloudfunctions.googleapis.com` [cite: 1]
* `pubsub.googleapis.com` [cite: 1]
* `firestore.googleapis.com` [cite: 1]
* `cloudbuild.googleapis.com` [cite: 1]
* `secretmanager.googleapis.com` [cite: 1]
* `run.googleapis.com` [cite: 1]
* `workflows.googleapis.com` [cite: 1]
* `iam.googleapis.com` [cite: 1]
* `artifactregistry.googleapis.com` [cite: 1]
* `storage.googleapis.com` [cite: 1]

---

## II. GitHub & CI/CD Configuration

### 1. Repository
* **Repository:** `Huyen1974/chatgpt-githubnew` [cite: 1]
* **Branches:**
    * Test: `test` [cite: 1]
    * Production: `main` [cite: 1]

### 2. GitHub Secrets (Actions Secrets)
* **Test Environment (Nhánh `test`):**
    * `PROJECT_ID_TEST`: `chatgpt-db-project` [cite: 1]
    * `GCP_SERVICE_ACCOUNT_TEST`: `gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com` (Xác nhận lại email này) [cite: 1]
    * `GCP_WORKLOAD_IDENTITY_PROVIDER_TEST`: `projects/1042559846495/locations/global/workloadIdentityPools/github-test-pool/providers/github-test-provider` [cite: 1]
* **Production Environment (Nhánh `main`):**
    * `PROJECT_ID`: `github-chatgpt-ggcloud` [cite: 1]
    * `GCP_SERVICE_ACCOUNT`: `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com` [cite: 1]
    * `GCP_WORKLOAD_IDENTITY_PROVIDER`: `projects/812872501910/locations/global/workloadIdentityPools/github-pool/providers/github-provider` [cite: 1]
* **Common Secrets (Sử dụng cho cả 2 môi trường):**
    * `DOCKERHUB_USERNAME`: `nguyenminhhuyen` [cite: 1]
    * `DOCKERHUB_PASSWORD`: (Stored, used for CI/CD, không hiển thị giá trị) [cite: 1]
    * `GH_TOKEN`: (Stored, scopes: `read:org`, `repo`, `workflow`, không hiển thị giá trị) [cite: 1]

### 3. CI/CD Workflows (.github/workflows/)
* **Trigger:** Push code lên branch tương ứng (`main` hoặc `test`) hoặc manual dispatch (`workflow_dispatch`). [cite: 1]
* **Authentication:** Sử dụng Google GitHub Actions `auth` với Workload Identity Federation và Service Account tương ứng. [cite: 1]
* **Permissions:** `contents: read`, `id-token: write`. [cite: 1]
* **Files:**
    * `deploy_functions.yaml`: Deploy Cloud Functions từ thư mục `functions/`. [cite: 1]
    * `deploy_containers.yaml`: Build Docker images từ `containers/`, push lên Artifact Registry, và deploy lên Cloud Run. [cite: 1]
    * `deploy_workflows.yaml`: Deploy Cloud Workflows từ các file `.yaml` trong thư mục `workflows/`. [cite: 1]
* **Key Parameters & Commands (Ví dụ cho Production - Nhánh `main`):**
    * **Functions (`deploy_functions.yaml`):**
        * Trigger Path: `functions/**`, `.github/workflows/deploy_functions.yaml` [cite: 1]
        * Python Version: `3.10` [cite: 1]
        * Dependencies: `pip install -r requirements.txt` [cite: 1]
        * Deploy Command:
          ```bash
          gcloud functions deploy "$FUNCTION_NAME" \
            --region=asia-southeast1 \
            --runtime=python310 \
            --trigger-http \
            --allow-unauthenticated \
            --source="$FUNCTION_DIR" \
            --entry-point="$ENTRY_POINT" \
            --project=${{ secrets.PROJECT_ID }}
          ``` [cite: 1]
    * **Containers (`deploy_containers.yaml`):**
        * Trigger Path: `containers/**`, `.github/workflows/deploy_containers.yaml` [cite: 1]
        * Docker Configure: `gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet` [cite: 1]
        * Build & Push:
          ```bash
          IMAGE="asia-southeast1-docker.pkg.dev/${{ secrets.PROJECT_ID }}/docker-repo/$CONTAINER_NAME:latest"
          docker build -t "$IMAGE" "$CONTAINER_DIR"
          docker push "$IMAGE"
          ``` [cite: 1]
        * Deploy to Cloud Run:
          ```bash
          gcloud run deploy "$CONTAINER_NAME" \
            --image "$IMAGE" \
            --region asia-southeast1 \
            --platform managed \
            --allow-unauthenticated \
            --service-account=${{ secrets.GCP_SERVICE_ACCOUNT }}
          ``` [cite: 1]
    * **Workflows (`deploy_workflows.yaml`):**
        * Trigger Path: `workflows/**`, `.github/workflows/deploy_workflows.yaml` [cite: 1]
        * Deploy Command:
          ```bash
          gcloud workflows deploy "$WORKFLOW_NAME" \
            --source="$WORKFLOW_FILE" \
            --location=asia-southeast1
          ``` [cite: 1]
* **Lưu ý cho Nhánh `test`:** Các workflow tương tự nhánh `main` nhưng sử dụng secrets và trigger branch `test` (`on.push.branches: [ "test" ]`). [cite: 1]

---

## III. Local Development Environment Setup (MacBook M1 - User nmhuyen)

*Thông tin ghi nhận đến ngày 26/03/2025* [cite: 3]

### 1. System Information
* **Shell:** `zsh` (mặc định macOS) [cite: 3]

### 2. Python & PIP
* **System Python (via Homebrew):**
    * Phiên bản: `3.13.1` [cite: 3]
    * Đường dẫn: `/opt/homebrew/bin/python3` [cite: 3]
* **Current Virtual Environment (`venv`):**
    * Đường dẫn: `/Users/nmhuyen/Documents/GitHub/chatgpt-githubnew_TEST/venv` [cite: 3]
    * Python Version: `3.13` [cite: 3]
    * PIP Version: `25.0.1` (từ `/venv/lib/python3.13/site-packages/pip`) [cite: 3]
    * **Key Packages Installed:** [cite: 3]
        * `functions-framework==3.5.0`
        * `Flask==2.3.3`
        * `google-cloud-secret-manager==2.23.2`
        * `google-cloud-firestore==2.20.1`
        * `openai==1.68.2`

### 3. Homebrew
* **Phiên bản:** `4.4.16` [cite: 3]
* **Key Formulae Installed:** `python@3.13`, `python@3.11`, `terraform`, `go`, `node`, `php` [cite: 3]
* **Key Casks Installed:** `docker` (Docker Desktop), `google-cloud-sdk` [cite: 3]

### 4. Google Cloud SDK (`gcloud`)
* **Phiên bản:** `504.0.1` [cite: 3]
* **Installation Method:** Homebrew Cask (`google-cloud-sdk`) [cite: 3]
* **Components:** `alpha`, `beta`, `bq`, `core`, `gcloud-crc32c`, `gsutil` [cite: 3]

### 5. Other Tools
* **Docker:** Installed via Homebrew Cask (`docker`) [cite: 3]
* **Terraform:** Installed via Homebrew (`terraform`) [cite: 3]
* **VS Code Extensions:** `ms-python.python` (using Python 3.13.1 from Homebrew) [cite: 3]
* **Ghi chú:** Các công cụ cơ bản như `git`, `curl` có thể đã được cài đặt. [cite: 3]

---

## IV. Important Notes & Conventions

* **Naming Convention:** Luôn sử dụng dấu gạch dưới (`_`) thay vì dấu gạch ngang (`-`) cho tên thư mục, file, và tài nguyên Cloud (ví dụ: `new_function`, không dùng `new-function`). [cite: 1, 4]
* **Project Verification:** **Luôn luôn** kiểm tra project Google Cloud hiện tại bằng lệnh `gcloud config get-value project` trước khi thực hiện bất kỳ lệnh `gcloud` nào, đặc biệt là deploy. [cite: 1, 4]
* **`--project` Flag:** Khuyến nghị **luôn luôn** sử dụng cờ `--project <PROJECT_ID>` trong mọi lệnh `gcloud` để tránh deploy nhầm môi trường. Không dựa vào project mặc định đã cấu hình. [cite: 1]
* **Secret Management:** Secrets được quản lý tập trung tại project Production (`github-chatgpt-ggcloud`) cho cả hai môi trường. Function `generate-lark-token` chịu trách nhiệm cập nhật `lark-access-token-sg`. [cite: 1, 2]
* **Workflow Paths:** Đảm bảo các đường dẫn (`paths`) trong trigger của workflow (`on.push.paths`) bao gồm cả file workflow tương ứng để workflow tự động chạy lại khi file cấu hình của nó thay đổi. [cite: 1]
* **Deployment Steps:** Quy trình 7 bước (được mô tả trong file `7 bước & hạ tầng NGẮN.txt`) nên được tuân thủ khi triển khai code mới từ `test` sang `main`. [cite: 4]


---

## 8. Quy trình Triển khai Thủ công (Manual Deployment)

**Lưu ý:** Ngoài quy trình CI/CD tự động qua GitHub Actions (mục 3), một số Cloud Functions đặc biệt có thể được triển khai thủ công theo quy trình dưới đây. AI cần lưu ý sự khác biệt này khi được yêu cầu cập nhật hoặc tạo code liên quan đến các function này.

* **Khi áp dụng:** [274-277]
    * Function có nhiều biến môi trường phức tạp, khó quản lý qua CI/CD YAML.
    * Cần triển khai nhanh để test mà không cần commit code vào repo chính.
    * Cần kiểm soát triển khai thủ công, tách biệt khỏi pipeline tự động.
    * Function ít thay đổi hoặc cần sự tách biệt đặc biệt.
* **Vị trí mã nguồn:** Mã nguồn cho các function này được lưu trữ **bên ngoài** repository GitHub chính, tại đường dẫn cục bộ như `/Users/nmhuyen/Documents/Manual Deploy/<function_name>/`. [278, 279] (AI sẽ không có quyền truy cập trực tiếp vào mã nguồn này, chỉ cần biết nó tồn tại tách biệt).
* **Công cụ triển khai:** Sử dụng lệnh `gcloud functions deploy` trực tiếp từ máy local. [286, 294]
* **Biến môi trường (Env Vars):** Được chỉ định trực tiếp trong lệnh `gcloud` bằng cờ `--set-env-vars="KEY1=value1,KEY2=value2,..."`. [286, 294]
* **Quy trình:**
    1.  Soạn mã và `requirements.txt` trong thư mục local riêng (`/Users/nmhuyen/Documents/Manual Deploy/<function_name>/`). [281]
    2.  Deploy lên project **Test** (`chatgpt-db-project`) bằng `gcloud functions deploy ... --project=chatgpt-db-project ... --source="/path/to/manual/deploy/dir"`. [284, 286]
    3.  Kiểm tra kỹ lưỡng trên môi trường Test. [288]
    4.  Deploy lên project **Production** (`github-chatgpt-ggcloud`) bằng `gcloud functions deploy ... --project=github-chatgpt-ggcloud ... --source="/path/to/manual/deploy/dir"`. [292, 294]
    5.  Kiểm tra kỹ lưỡng trên môi trường Production. [296]
    6.  Ghi lại báo cáo triển khai thủ công (`report.md`). [300]
* **Service Accounts:** Sử dụng cùng Service Account như luồng CI/CD cho môi trường tương ứng:
    * Test: `gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com` [285]
    * Production: `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com` [293]
* **Quan trọng:** Các function được triển khai theo quy trình này **KHÔNG** được quản lý bởi các file workflow trong `.github/workflows/`. Mọi thay đổi hoặc cập nhật cho chúng phải được thực hiện thủ công bằng `gcloud`. [307, 309]

---