**📦 QDRANT LAW (Luật về Qdrant) – Version 1.2**

**Updated:** August 05, 2025 **Purpose:** Quy định các quy tắc cụ thể
cho việc vận hành Qdrant trong dự án Agent Data Langroid, tuân thủ
**Hiến pháp v1.11e**. **Scope:** Áp dụng cho Qdrant Cloud cluster, các
collection, và các tài nguyên phụ trợ (ví dụ: Cloud Function
manage\_qdrant).

**Changes from v1.1:**

- Làm rõ và bổ sung các yêu cầu kỹ thuật bắt buộc cho Cloud Function
  manage\_qdrant, bao gồm biến môi trường, logging, và quy trình
  snapshot.

- Cập nhật Phụ lục Nợ Kỹ thuật cho rõ ràng hơn.

**Bảng Ánh xạ tới Hiến pháp**

<table>
<colgroup>
<col style="width: 21%" />
<col style="width: 30%" />
<col style="width: 48%" />
</colgroup>
<thead>
<tr>
<th>Mục của QD-LAW</th>
<th>Ánh xạ tới Nguyên tắc Hiến pháp</th>
<th>Rationale (Lý do)</th>
</tr>
</thead>
<tbody>
<tr>
<td>§1: Cấu trúc Cluster</td>
<td>HP-II (Naming), HP-QD-03 (Shared Cluster)</td>
<td>Chuẩn hóa quy ước đặt tên và mô hình sử dụng cluster dùng
chung.</td>
</tr>
<tr>
<td>§2: Quản lý Collection</td>
<td>HP-II (Collection Naming)</td>
<td>Quy định cách đặt tên để phân tách dữ liệu các môi trường.</td>
</tr>
<tr>
<td>§3: Đồng bộ Metadata</td>
<td>HP-DR-02 (Data Sync)</td>
<td>Bắt buộc phải có sự nhất quán giữa vector và metadata.</td>
</tr>
<tr>
<td>§4: Quản lý Vận hành</td>
<td>HP-02 (IaC Tối thiểu)</td>
<td>Định nghĩa các công cụ tự động hóa để quản lý trạng thái và chi phí
của cluster.</td>
</tr>
<tr>
<td>§5: Quản lý Secrets</td>
<td>HP-05, HP-SEC-02</td>
<td>Tuân thủ mô hình quản lý secrets tập trung và chính sách luân
chuyển.</td>
</tr>
<tr>
<td>§6: Chính sách Vùng</td>
<td>HP-II (Qdrant Cluster)</td>
<td>Tuân thủ chính sách vùng và kế hoạch di dời đã được Hiến pháp phê
duyệt.</td>
</tr>
<tr>
<td>§7: Phục hồi Thảm họa (DR)</td>
<td>HP-DR-01</td>
<td>Chi tiết hóa các yêu cầu về sao lưu cho Qdrant, tuân thủ các Luật
khác.</td>
</tr>
</tbody>
</table>

Xuất sang Trang tính

**§1: Cấu trúc Cluster** 1.1.

**Mô hình:** Hệ thống BẮT BUỘC sử dụng mô hình **cluster dùng chung
(shared cluster)** cho cả môi trường Test và Production.

1.2.

**Quy ước Đặt tên:** Tên của cluster BẮT BUỘC phải tuân thủ quy ước đã
được phê duyệt trong Điều II của Hiến pháp
(agent-data-vector-dev-useast4).

**§2: Quản lý Collection** 2.1.

**Quy ước Đặt tên:** Việc phân tách dữ liệu giữa các môi trường BẮT BUỘC
phải được thực hiện bằng cách sử dụng các collection riêng biệt, với tên
tuân thủ định dạng &lt;env&gt;\_documents.

2.2.

**Ví dụ:** test\_documents cho môi trường Test, production\_documents
cho môi trường Production.

**§3: Đồng bộ Metadata** 3.1. Mọi thao tác ghi hoặc cập nhật vector vào
Qdrant BẮT BUỘC phải được thực hiện song song với việc ghi hoặc cập nhật
metadata tương ứng vào Firestore, tuân thủ nguyên tắc HP-DR-02.

3.2. Trong trường hợp quy trình đồng bộ gặp lỗi, hệ thống phải gửi cảnh
báo và cho phép thực hiện fallback thủ công kèm theo bản ghi kiểm toán.

**§4: Quản lý Vận hành (Cloud Function)** 4.1. Một Cloud Function tên là

manage\_qdrant BẮT BUỘC phải được triển khai để quản lý trạng thái vận
hành của Qdrant cluster.

4.2. Function này BẮT BUỘC phải cung cấp các giao diện (action) tối
thiểu sau: \* start (để kích hoạt lại cluster) \* stop (**BẮT BUỘC**
phải tạo snapshot trước khi tạm dừng cluster) \* status (để kiểm tra
trạng thái) \* touch (để làm mới bộ đếm thời gian không hoạt động) 4.3.

**Cấu hình Scheduler:** Một Cloud Scheduler BẮT BUỘC phải được cấu hình
để gọi đến action touch của function này một cách định kỳ (khuyến nghị:
mỗi 10 phút) nhằm ngăn chặn việc cluster tự động tạm dừng.

4.4. **Quyền Thực thi:** Service Account được sử dụng bởi Cloud
Scheduler BẮT BUỘC phải được cấp quyền roles/cloudfunctions.invoker để
có thể kích hoạt Cloud Function. 4.5. **Biến môi trường:** Function BẮT
BUỘC phải được cấu hình với các biến môi trường cần thiết, tối thiểu bao
gồm: PROJECT\_ID, QDRANT\_CLUSTER\_ID, QDRANT\_API\_KEY. 4.6.
**Logging:** Function BẮT BUỘC phải sử dụng cơ chế ghi log có cấu trúc
(Structured Logging) để phục vụ việc giám sát và gỡ lỗi.

**§5: Quản lý Secrets** 5.1. Các secret của Qdrant (API key, management
key) BẮT BUỘC phải được quản lý theo mô hình tập trung đã được định
nghĩa tại HP-05 của Hiến pháp và chi tiết hóa trong GH-LAW §5.

5.2. Việc luân chuyển (rotation) các secret này BẮT BUỘC phải tuân thủ
chính sách đã định tại HP-SEC-02 (90 ngày cho production, 120 ngày cho
test).

**§6: Chính sách Vùng** 6.1. Qdrant cluster BẮT BUỘC phải được triển
khai tại vùng

us-east4 theo đúng ngoại lệ đã được phê duyệt trong Hiến pháp và GC-LAW
§5 .

6.2. Một kế hoạch di dời (migration) sang vùng

asia-southeast1 phải được chuẩn bị và sẵn sàng thực thi khi Qdrant Cloud
chính thức hỗ trợ .

**§7: Phục hồi Thảm họa (DR) & Sao lưu** 7.1. Cơ chế sao lưu tự động
(snapshot) BẮT BUỘC phải được thiết lập theo nguyên tắc HP-DR-01 và các
ghi chú về sự phụ thuộc vào bậc dịch vụ (tier).

7.2.

**Tần suất sao lưu** BẮT BUỘC phải tuân thủ quy định tối thiểu trong
GC-LAW §7.2: hàng ngày cho production, hàng tuần cho test.

7.3.

**Đích đến của bản sao lưu** BẮT BUỘC phải là GCS Bucket chuyên dụng,
tuân thủ quy ước đặt tên đã định trong TF-LAW §10.2
(...-backup-&lt;env&gt;).

**Phụ lục A – Nợ Kỹ thuật**

<table>
<colgroup>
<col style="width: 9%" />
<col style="width: 12%" />
<col style="width: 66%" />
<col style="width: 11%" />
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
<td>TD-QD-01</td>
<td>Sao lưu Tự động</td>
<td><strong>Di dời lên bậc trả phí (Paid Tier) để có tính năng sao lưu
tự động qua API, tuân thủ nguyên tắc DR.</strong></td>
<td>31-12-2025</td>
</tr>
</tbody>
</table>
