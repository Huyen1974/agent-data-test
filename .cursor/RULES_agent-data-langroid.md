📂 Final: .cursor/RULES_agent-data-langroid.md (Cập nhật 30.07.2025)

# ⛔ CURSOR RULES – Agent Data Langroid (critical)

## 1. Project root (edit‑allowed ONLY)
/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid
✅ Mọi thao tác phải nằm trong thư mục này.
⛔ Không được đọc/ghi/sửa ngoài path.
### GH Auth Bootstrap (bắt buộc trước khi dùng `gh`)
- **Project GSM**: `github-chatgpt-ggcloud`
- **Service Account điều hành**: `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com`
- **Secret**: `gh_pat_sync_secrets` (PAT có scopes: repo, workflow)

**Cách chạy:**
```bash
# Xác thực và đăng nhập (nếu cần)
PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" scripts/bootstrap_gh.sh apply
# Kiểm tra trạng thái đăng nhập
gh auth status -h github.com

---

## 2. GitHub repositories
Bạn đang làm việc với đúng 2 repo:
- `agent-data-test`
- `agent-data-production`

⛔ Không được thao tác với bất kỳ repo nào khác.

---

## 3. Artifact Registry
Mỗi repo sẽ có Artifact Registry riêng tương ứng:
- `agent-data-test`
- `agent-data-production`

☑️ Lưu Docker, Cloud Functions, Cloud Run... Không tách nhỏ.

---

## 4. CI/CD – Kỷ luật tuyệt đối
✅ Mỗi thay đổi phải đảm bảo CI xanh toàn phần: Cloud Function, Cloud Run, Workflow YAML.

⛔ Không được merge khi CI còn đỏ dù chỉ 1 bước.
⛔ Không dùng `continue-on-error: true` trong mọi bước test hoặc validate.

---

## 5. Terraform buckets (do Terraform quản lý)

| Bucket Name                                           | Repo        |
|------------------------------------------------------|-------------|
| huyen1974-agent-data-artifacts-test                  | test        |
| huyen1974-agent-data-artifacts-production            | production  |
| huyen1974-agent-data-knowledge-test                  | test        |
| huyen1974-agent-data-knowledge-production            | production  |
| huyen1974-agent-data-logs-test                       | test        |
| huyen1974-agent-data-logs-production                 | production  |
| huyen1974-agent-data-qdrant-snapshots-test           | test        |
| huyen1974-agent-data-qdrant-snapshots-production     | production  |
| huyen1974-agent-data-source-test                     | test        |
| huyen1974-agent-data-source-production               | production  |
| huyen1974-agent-data-tfstate-test                    | test        |
| huyen1974-agent-data-tfstate-production              | production  |

➡️ Terraform phải giữ quyền trên các bucket này theo đúng repo tương ứng.

---

## 6. 🔐 SECRETS & IAM (baseline chuẩn nhất)

| Purpose                  | GitHub secret              | Example / Note                             |
|--------------------------|----------------------------|---------------------------------------------|
| GCP project ID           | `GCP_PROJECT_ID`           | `github-chatgpt-ggcloud`                    |
| Deployer SA              | `GCP_SERVICE_ACCOUNT`      | `chatgpt-deployer@...`                      |
| WIF provider             | `GCP_WIF_PROVIDER`         | `projects/.../providers/...`                |
| WIF pool ID              | `GCP_WIF_POOL`             | e.g. `gha-pool`                             |
| SA fallback key (base64) | `GCP_SA_KEY_JSON`          | Dùng nếu WIF lỗi                            |
| OpenAI Key               | `OPENAI_API_KEY`           | runtime                                     |
| Lark app secret          | `LARK_APP_SECRET`          | runtime                                     |
| Qdrant mgmt key          | `QDRANT_CLOUD_MGMT_KEY`    | cho tạo/xoá cluster                         |
| Qdrant cluster 1 ID      | `QDRANT_CLUSTER1_ID`       | e.g. `N1D8R2vC0_5`                           |
| Qdrant cluster 1 key     | `QDRANT_CLUSTER1_KEY`      | auth key cụ thể cho cluster trên            |

> Quy ước thêm: `QDRANT_CLUSTER{N}_KEY` / `QDRANT_CLUSTER{N}_ID`

🌐 GCP secrets lưu tại `github-chatgpt-ggcloud` → Secret Manager
🔐 GitHub Secrets lưu tại `agent-data-test` / `agent-data-production`

---

## 7. IAM roles (đã phân quyền)

✅ Bắt buộc giữ:
- `roles/viewer`, `roles/cloudasset.viewer`, `roles/artifactregistry.writer`
- `roles/cloudfunctions.developer`, `roles/iam.serviceAccountUser`
- `roles/run.admin`, `roles/logging.logWriter`, `roles/secretmanager.secretAccessor`
- `roles/serviceusage.serviceUsageAdmin`, `roles/storage.admin`

⛔ Cấm gán thêm:
- `roles/secretmanager.admin`, `roles/iam.serviceAccountAdmin`
- `roles/cloudscheduler.admin`, `roles/cloudsql.*`, `roles/pubsub.publisher`
- `roles/cloudbuild.builds.editor`, `roles/run.invoker`, `roles/workflows.admin`

---

## 8. Kiểm soát CI & test count
### CI Verification Rules
- Mọi commit phải pass CI với `conclusion == success`
- Dùng các lệnh kiểm tra:
```bash
gh run view --log
gh run list -L1
gh run watch --exit-status --interval 15 --timeout 900
```
- Terraform: TF_EXIT phải là 0 hoặc 2
- ⛔ Cấm tuyệt đối dùng continue-on-error trong bất kỳ job test/lint/validate

### Test Count Rules (Manifest Drift & Baseline)
Nguyên tắc: Mọi thay đổi về số lượng file trong thư mục tests/ phải được kiểm soát chặt chẽ thông qua cơ chế "Manifest Drift" (CP0.4).
- ✅ Cơ chế kiểm soát: CI sẽ chạy lệnh: `python scripts/check_manifest.py`
  Lệnh này sẽ so sánh số lượng file trong thư mục tests/ với số lượng đã chốt trong file test_manifest_baseline.txt
- ❌ CI sẽ thất bại nếu số lượng file không khớp (Manifest drift ≠ 0)

### Quy trình cập nhật baseline hợp lệ:
1. Viết file test mới ➜ commit trước đó phải CI xanh
2. Chạy lệnh: `python scripts/collect_manifest.py > test_manifest_baseline.txt`
3. Commit cùng lúc:
   - Các file test mới
   - File test_manifest_baseline.txt cập nhật
4. Mô tả commit phải ghi rõ lý do thay đổi số lượng test
5. CI sau commit phải xanh

⛔ Cursor không được chỉnh sửa test mà không cập nhật manifest. Không được tự thêm test nếu chưa pass đủ CI + update manifest.
📌 Đây là cơ chế bắt buộc để giữ số lượng test ổn định, tránh báo cáo ảo hoặc CI rác.

---

## 9. Báo cáo & tự sửa lỗi (strict)
Cursor không được báo "PASS" nếu chưa verify bằng log CI.

Nếu CI đỏ, phải:
1. Kiểm tra log `gh run view`
2. Tự sửa lỗi và push lại cùng branch
3. Lặp lại tối đa 3 lần, nếu vẫn fail mới được báo lỗi

---

## 10. E2E Tests (CPG1.1, CPG1.2) - Kiểm soát chặt chẽ

### Quy tắc E2E Tests
- E2E tests (CPG1.1 Qdrant connectivity, CPG1.2 OpenAI connectivity) chỉ được chạy khi:
  - Pull request có label `e2e` được gán thủ công
  - Workflow dispatch được kích hoạt thủ công với input `e2e: true`
- ⛔ **TUYỆT ĐỐI KHÔNG** chạy E2E tests trong normal PR hoặc push để giữ CI nhanh

### Cấu hình E2E Tests
- **Workflow**: `.github/workflows/agent-e2e.yml`
- **Dependencies**: `langroid==0.58.0`, `pytest`
- **Environment**: `OPENAI_API_KEY`, `QDRANT_CLUSTER1_KEY`, `QDRANT_CLUSTER1_ID`
- **Collection**: `test_documents` (cleaned before each run)
- **Embedding**: `text-embedding-3-small` (OpenAI)
- **Region**: `asia-southeast1`

### Validation Requirements
- **CPG1.1**: Response metadata phải cite `test_documents` collection (Qdrant connectivity)
- **CPG1.2**: Real responses generated với `mock_data: false` (OpenAI connectivity)
- **Collection Info**: Đúng embedding model và distance metric
- **Regional Config**: Đúng asia-southeast1 region

### Command Sequence
```bash
python scripts/gen_fixtures.py --no-mock
pytest tests/test_fixture_pipeline.py -m fixture --disable-warnings
```

---

## 11. Bảo vệ RULES – Không được xóa
- Khi cập nhật RULES, Cursor tuyệt đối không được xoá bất kỳ nội dung nào nếu Prompt không cho phép rõ ràng.
- Chỉ được thêm phần mới nếu Prompt không nói về xoá.
- Tất cả cập nhật rules phải commit cùng commit logic.
- Khi remove workflow, dùng `git rm`, không dùng `rm -f`

✅ Đây là quy tắc chuẩn cứng Agent Data Langroid – Cursor phải luôn tuân thủ tuyệt đối.

🕘 Cập nhật: 2025-07-30
