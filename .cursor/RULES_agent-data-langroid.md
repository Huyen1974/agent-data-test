**📜 File Quy tắc Dự án: RULES_agent-data-langroid.md (Version 1.1)**

**Cập nhật:** August 06, 2025 (Phiên bản tuân thủ Hiến pháp v1.11e và
các Luật liên quan)

**⛔ QUY TẮC CURSOR -- DỰ ÁN AGENT DATA LANGROID (Bản Hoàn Chỉnh)**

*Tài liệu này là nguồn chân lý duy nhất cho mọi hoạt động của bạn. Mọi
hành động phải tuân thủ nghiêm ngặt các quy tắc dưới đây.*

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

- **Kiểm tra nhanh WIF:** Trước khi đẩy các thay đổi liên quan đến quyền
  hạn, bạn nên chạy lệnh sau trên máy cục bộ để mô phỏng và kiểm tra các
  điều kiện WIF: gcloud auth application-default login
  --impersonate-service-account=$GCP_SERVICE_ACCOUNT

**2. Quy tắc Quản lý Hạ tầng (Terraform)**

- **Quy ước Đặt tên Bucket:** Mọi bucket được tạo ra BẮT BUỘC phải tuân
  thủ định dạng \<standard-prefix\>-agent-data-\<purpose\>-\<env\>.

  - standard-prefix có giá trị là huyen1974.

  - Quy tắc về ký tự: Bắt buộc dùng dấu gạch ngang (

> -), cấm tuyệt đối dấu gạch dưới (\_).

- **Danh sách Bucket Cụ thể:** Dưới đây là danh sách các bucket được
  Terraform quản lý.

  ------------------------------------------------------------------------------------
  Tên Bucket                                         Mục đích           Môi trường
                                                     (\<purpose\>)      (\<env\>)
  -------------------------------------------------- ------------------ --------------
  huyen1974-agent-data-artifacts-test                artifacts          test

  huyen1974-agent-data-artifacts-production          artifacts          production

  huyen1974-agent-data-knowledge-test                knowledge          test

  huyen1974-agent-data-knowledge-production          knowledge          production

  huyen1974-agent-data-logs-test                     logs               test

  huyen1974-agent-data-logs-production               logs               production

  huyen1974-agent-data-qdrant-snapshots-test         qdrant-snapshots   test

  huyen1974-agent-data-qdrant-snapshots-production   qdrant-snapshots   production

  huyen1974-agent-data-source-test                   source             test

  huyen1974-agent-data-source-production             source             production

  huyen1974-agent-data-tfstate-test                  tfstate            test

  huyen1974-agent-data-tfstate-production            tfstate            production

  huyen1974-agent-data-backup-test                   backup             test

  huyen1974-agent-data-backup-production             backup             production
  ------------------------------------------------------------------------------------

- Ghi chú: Tất cả các bucket mới BẮT BUỘC phải bật Uniform Bucket-Level
  Access (UBLA) để tuân thủ **Hiến pháp (HP-02)** và **TF-LAW (§4.3)**.

- Ghi chú bổ sung: Một số bucket được tạo trước khi Hiến pháp có hiệu
  lực có thể chưa bật UBLA. Các bucket này được coi là \"legacy\" và sẽ
  được xử lý theo nợ kỹ thuật **TD-TF-01**.

**3. Quản lý Artifacts & Docker Images**

- **Nơi lưu trữ:** Mọi Docker images, Cloud Functions và các artifact
  khác phải được lưu trữ trên **Google Artifact Registry**.

- **Phân tách môi trường:** Sẽ có các repository riêng biệt trong
  Artifact Registry cho mỗi môi trường: agent-data-test và
  agent-data-production .

- **Chính sách Lưu giữ (Retention):** Việc lưu giữ artifact BẮT BUỘC
  phải tuân thủ quy trình 2 giai đoạn:

  - **14 ngày:** Các artifact sẽ được tự động đánh dấu là \"stale\" (cũ)
    để cảnh báo sớm.

  - **30 ngày:** Một quy trình tự động sẽ tạo GitHub Issue \[CLEANUP\]
    để yêu cầu phê duyệt dọn dẹp. Việc xóa bỏ chỉ được thực hiện thủ
    công sau khi Issue được đóng lại.

  - Báo cáo và Cảnh báo: Một báo cáo tự động hàng tuần qua Slack sẽ tổng
    hợp số lượng artifact đang được đánh dấu \"stale\". Báo cáo này BẮT
    BUỘC phải được cấu hình với một ngưỡng cảnh báo (ví dụ: stale_count
    \< 5) và sẽ gửi một cảnh báo đặc biệt nếu số lượng vượt ngưỡng này.

### **4. Quản lý Dữ liệu (Firestore & Metadata) 4.1. Quy tắc Quản lý Qdrant**

- **Tên Cluster:** Cluster bạn làm việc có tên là
  agent-data-vector-dev-useast4.

- **Tên Collection:** Tên collection BẮT BUỘC phải theo định dạng
  \<env\>\_documents (ví dụ: test_documents, production_documents).

- **Vận Quản lý Trạng thái Cluster:** Mọi tác vụ vận hành (ví dụ: tạm
  dừng cluster để tiết kiệm chi phí) BẮT BUỘC phải được thực hiện thông
  qua Cloud Function manage_qdrant. Cụ thể, khi cần tạm dừng cluster,
  bạn phải gọi đến action stop, vì action này đã bao gồm bước tạo
  snapshot an toàn theo yêu_cầu của **QD-LAW §4.2**.

<!-- -->

- **Vai trò của Firestore:** Firestore được sử dụng cho hai mục đích
  chính:

  1.  Lưu trữ

> **Session Memory** cho Agent.

2.  Lưu trữ

> **Metadata** cho các vector trong Qdrant.

- **Nguyên tắc Đồng bộ Bất biến:** Mọi thao tác ghi hoặc cập nhật vector
  vào Qdrant BẮT BUỘC phải được thực hiện song song với việc ghi hoặc
  cập nhật metadata tương ứng vào Firestore .

- Trong trường-hợp quy trình đồng bộ này gặp lỗi, hệ thống phải có cơ
  chế gửi cảnh báo ngay lập tức cho Owner (ví dụ: qua Slack) để xử lý
  thủ công.

- **Cấu trúc Metadata:** Cấu trúc chi tiết của metadata và các nhãn sẽ
  được định nghĩa trong các tài liệu thiết kế chuyên sâu. Nhiệm vụ của
  bạn là tuân thủ các cấu trúc đã được định nghĩa trong mã nguồn (ví dụ:
  Pydantic models).

**5. Quy tắc CI/CD & GitHub**

- **Kiểm soát Lockfile:** Lockfile (requirements.txt) BẮT BUỘC phải được
  tạo bằng lệnh pip-compile --no-upgrade. CI sẽ có bước

> git diff --exit-code requirements.txt để đảm bảo file không bị chỉnh
> sửa thủ công .

- **Pre-commit Hooks:** Mọi commit BẮT BUỘC phải vượt qua các hook đã
  được định nghĩa trong .pre-commit-config.yaml (bao gồm black, ruff,
  trufflehog, manifest-drift).

- **Pass-gate:** Một Pull Request chỉ được merge khi tất cả các status
  check sau thành công: lint-only, terraform-plan, secret-scan,
  agent-e2e, manifest-drift-check.

- **continue-on-error:** BỊ CẤM TUYỆT ĐỐI, ngoại trừ trường hợp duy nhất
  cho bước \"auth fallback\" trong workflow.

- **Định dạng Tag Release:** Các tag cho production release BẮT BUỘC
  phải theo định dạng vX.Y.Z (ví dụ: v1.2.3).

- **Giám sát Nợ Kỹ thuật:** Cho đến khi dashboard giám sát vận hành
  (agent-data-ops) được triển khai đầy đủ theo **Hiến pháp
  (HP-OBS-01)**, các workflow CI chính BẮT BUỘC phải in ra một cảnh báo
  (::warning::) nếu các chỉ số về chi phí CI và độ trễ OpenAI chưa được
  giám sát.

**6. Quản lý Secrets (CỰC KỲ QUAN TRỌNG)**

- **Nguồn Chân lý:** **Google Secret Manager** là nguồn duy nhất cho giá
  trị của secrets.

- **Cơ chế Đồng bộ:** Secrets trên GitHub được quản lý **TẬP TRUNG**.
  Một workflow

> sync-secrets.yml tại repo chatgpt-githubnew là quy trình **DUY NHẤT**
> được phép ghi (secrets:write) secrets lên các repo agent-data-test và
> agent-data-production .

- [**Nhiệm vụ của Cursor:** Bạn **KHÔNG ĐƯỢC PHÉP** tạo, sửa, hoặc xóa
  secrets trực tiếp trên agent-data-test hoặc
  agent-data-production.]{.mark} Quy trình Xử lý Sự cố (Fallback)**:**
  Trong trường hợp workflow sync-secrets.yml gặp sự cố kéo dài (\>24h),
  việc cập nhật thủ công sẽ được thực hiện theo quy trình fallback đã
  quy định tại GH-LAW §5.5.

- **Danh sách Secrets:** Dưới đây là danh sách các secret bạn sẽ làm
  việc.

  -------------------------------------------------------------------------------------------
  Mục đích      Tên Secret trên GitHub  Ghi chú
  ------------- ----------------------- -----------------------------------------------------
  GCP Project   GCP_PROJECT_ID          Giá trị: github-chatgpt-ggcloud
  ID

  Deployer SA   GCP_SERVICE_ACCOUNT     Giá trị: chatgpt-deployer@\...

  WIF Provider  GCP_WIF_PROVIDER        projects/\.../providers/github-provider

  WIF Pool      GCP_WIF_POOL            projects/\.../workloadIdentityPools/agent-data-pool

  SA Fallback   GCP_SA_KEY_JSON         Dùng khi WIF lỗi
  Key

  OpenAI Key    OPENAI_API_KEY          Secret cho runtime

  Lark App      LARK_APP_SECRET         Secret cho runtime
  Secret

  Qdrant Mgmt   QDRANT_CLOUD_MGMT_KEY   Key quản lý Qdrant Cloud
  Key

  Qdrant        QDRANT_CLUSTER1_KEY     Key truy cập cluster
  Cluster Key

  Qdrant        QDRANT_CLUSTER1_ID      ID của cluster
  Cluster ID
  -------------------------------------------------------------------------------------------

- \*\*Chính sách Luân chuyển:\*\* Các secret quan trọng (ví dụ:
  QDRANT_CLUSTER1_KEY, OPENAI_API_KEY) phải được luân chuyển định kỳ: 90
  ngày cho môi trường production và 120 ngày cho môi trường test.

  - **Cảnh báo Luân chuyển:** Một workflow giám sát (secrets-audit.yml)
    BẮT BUỘC phải được thiết lập để chạy hàng ngày. Workflow này phải có
    khả năng gửi cảnh báo qua Slack khi một secret quan trọng còn **dưới
    15 ngày** là đến hạn luân chuyển.

**7. Quản lý Truy cập (IAM)**

- **Các quyền được phép cấp cho Service Account
  (chatgpt-deployer@\...):**

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

- **Giới hạn Retry:** Khi CI thất bại, bạn được phép tự động sửa lỗi và
  push lại cùng nhánh **tối đa 2 lần**. Sau lần thứ 2 nếu vẫn thất bại,
  BẮT BUỘC phải dừng lại và thông báo .

- **Kiểm soát Số lượng Test (Manifest Drift):**

  - **Nguyên tắc:** Mọi thay đổi về số lượng file test BẮT BUỘC phải
    được cập nhật vào file test_manifest_baseline.txt.

  - **Quy trình Cập nhật Hợp lệ:**

    1.  Hoàn thành và commit code cho các file test mới.

    2.  Chạy lệnh python scripts/collect_manifest.py \>
        test_manifest_baseline.txt để cập nhật file baseline.

    3.  Commit cả file test mới và file test_manifest_baseline.txt đã
        cập nhật trong **cùng một commit**.

    4.  Mô tả commit phải ghi rõ lý do thay đổi số lượng test.

- **\* \*Thời gian chờ:\*\* Phải có một khoảng thời gian chờ tối thiểu
  là 5 phút giữa các lần retry tự động.**

- **Xác minh Trước khi Báo cáo:** Bạn không được báo cáo một tác vụ là
  \"Thành công\" hoặc \"Hoàn thành\" cho đến khi đã xác minh trạng thái
  thành công (success) của nó bằng cách kiểm tra log của CI (ví dụ: gh
  run view).

**9. Quy tắc Bảo vệ RULES**

- Bạn tuyệt đối không được xóa bất kỳ nội dung nào trong file RULES này
  nếu không được yêu cầu rõ ràng.
