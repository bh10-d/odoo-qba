# Project Session State & Handover

Tài liệu này lưu trữ trạng thái làm việc và nhật ký bàn giao giữa các phiên làm việc (chat sessions).
**Mỗi phiên làm việc mới BẮT ĐẦU bằng việc đọc file này và KẾT THÚC bằng việc cập nhật file này.**

---

## 1. Thông Tin Môi Trường & Kiến Trúc Hiện Tại (Baseline)

- **Dự án:** QBA Odoo 18 Community (Phụ tùng ô tô xe tải nặng Q.BA)
- **Nhánh Git hiện tại:** `perf-optimize-qba-pos`
- **Môi trường Docker:**
  - `staging-qba-postgres-1`: PostgreSQL 15, Database chính: `qba`
  - `staging-qba-odoo-1`: Odoo 18.0 Community, Cổng Web: `http://localhost:8089` (Longpolling: `8092`)
- **Các Custom Addons đang cài đặt (`odoo/custom_addons/`):**
  - `qba`: Phụ tùng, đồng bộ Website SEO, in tem nhãn trực tiếp.
  - `qba_pos`: Điểm bán lẻ POS, bán hàng nhập tay `SP_CHUA_CO_MA`, bảo hành Zalo. Máy POS hiện tại: `POS Ban Le Q.BA` (3.106 sản phẩm đã kích hoạt).
  - `qba_ai`: Trợ lý AI tra cứu phụ tùng, kiểm tra tồn kho & báo giá thời gian thực.
- **Tích hợp Backend Ngoài (Express.js):**
  - Endpoint: `http://host.docker.internal:5000/api/v1`
  - Xác thực bảo mật: HMAC SHA-256 (`x-odoo-signature`, `x-odoo-timestamp`, `x-odoo-api-key`)
  - Trạng thái hiển thị giá: Chuẩn hóa nhãn `"Liên hệ Báo giá"` khi ẩn giá (`showPrice: false`).

---

## 2. Nhật Ký Phiên Gần Nhất (Last Session Log)

- **Thời gian:** 2026-11-06 11:25 (GMT+7)
- **Công việc đã hoàn thành:**
  1. Tích hợp bộ quy tắc **Ponytail** (`.agents/skills/ponytail*`, `.agents/rules/ponytail.md`) vào dự án.
  2. Tích hợp toàn diện **`odoo-senior-developer-skill-pack`** vào [.agents/](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/.agents) (10 Odoo skills, templates, workflows, `.agents/rules/odoo-senior.md`).
  3. Thiết lập **Mandatory Session Handover & Skill Activation Workflow**:
     - Tạo [SESSION_STATE.md](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/SESSION_STATE.md) làm file sổ tay ghi nhận trạng thái liên tục giữa các phiên.
     - Cập nhật quy tắc bắt đầu/kết thúc phiên vào [AGENTS.md](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/AGENTS.md) và [.agents/rules/session-handover.md](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/.agents/rules/session-handover.md).
  4. Cập nhật `.gitignore` cho phép theo dõi `AGENTS.md`, `SESSION_STATE.md`, `.agents/`.
  5. Đã commit (`0e9ef45`) và push toàn bộ cấu hình `.agents/`, `AGENTS.md`, `SESSION_STATE.md` lên Git remote (`origin feature/product-web-seo-sync`).
- **Các file chính đã thay đổi:**
  - `AGENTS.md` (Updated)
  - `SESSION_STATE.md` (Created & Initialized)
  - `.gitignore` (Updated)
  - `.agents/rules/session-handover.md` (Created)
  - `.agents/rules/odoo-senior.md` (Created)
  - `.agents/rules/ponytail.md` (Created)
  - `.agents/skills/*` (16 skills installed)

---

## 3. Bản Đồ Kích Hoạt Skills (Skill Activation Map)

Khi bắt đầu một tác vụ mới, AI bắt buộc phải đối chiếu và kích hoạt đúng skill tương ứng trước khi viết code:

| Tác vụ / Vấn đề cần xử lý | Skill áp dụng |
|---|---|
| Phân tích bài toán mới, xác định ranh giới module, lập kế hoạch | `.agents/skills/odoo-architect` |
| Viết model ORM, fields, compute, constraints, business logic, cron | `.agents/skills/odoo-backend` |
| Giao diện người dùng, OWL components, JS assets, QWeb templates, XML views | `.agents/skills/odoo-frontend` |
| Phân quyền, ACL (`ir.model.access.csv`), Record Rules, kiểm soát `sudo()` | `.agents/skills/odoo-security` |
| Tối ưu câu lệnh ORM, N+1 query, Index PostgreSQL, migration an toàn | `.agents/skills/odoo-database` |
| Viết Controller, Webhook, API client kết nối bên thứ 3 (Express, Zalo,...) | `.agents/skills/odoo-integration` |
| Phát triển hoặc debug AI Assistant, tìm kiếm ngữ nghĩa, RAG, prompt injection | `.agents/skills/odoo-ai-rag` |
| Viết unit test Odoo, kiểm thử bảo mật, kiểm chứng kết quả chạy test | `.agents/skills/odoo-testing` |
| Review code, đánh giá rủi ro trước khi commit hoặc merge | `.agents/skills/odoo-code-review` |
| Cấu hình Docker, kiểm tra log container, restart service, backup dữ liệu | `.agents/skills/odoo-devops` |
| Viết code tối giản, loại bỏ bloat, YAGNI, review diff tinh gọn | `.agents/skills/ponytail*` |
| Chống code rác, chống UI cliché, template sáo rỗng, comment máy móc | `.agents/skills/antislop*` |

---

## 4. Nhật Ký Phiên Vừa Thực Hiện

- **Thời gian:** 2026-11-06 15:58 (GMT+7)
- **Nhánh Git:** `perf-optimize-qba-pos`
- **Công việc đã hoàn thành:**
  1. Đã commit thành công nhánh `perf-optimize-qba-ai` (`06fd9cc`) và chuyển sang nhánh `perf-optimize-qba-pos`.
  2. **Giải quyết triệt để các phát hiện audit trên module `qba_pos`**:
     - **H1 (Rủi ro Lockout cao nhất)**: Tách HTTP call Zalo API ra ngoài DB transaction trong [`pos_order.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba_pos/models/pos_order.py). Sử dụng hook `self.env.cr.after('commit', lambda: ...)` sau khi đơn hàng POS đã commit xong hoàn toàn. Chấm dứt nguy cơ treo giữ khóa bản ghi đơn hàng khi mạng Zalo chậm.
     - **H2 (N+1 Category Sync)**: Batch tải danh sách `PosCategory` một lần duy nhất vào memory dictionary `{name: record}` trong [`product_template.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba_pos/models/product_template.py) thay vì chạy câu `search` lặp đi lặp lại per category.
     - **H3 (Index Trigram)**: Chuyển trường `name` trong [`pos_custom_product_history.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba_pos/models/pos_custom_product_history.py) sang `index="trigram"` native của Odoo 18 / PostgreSQL, tối ưu triệt để câu so khớp `=ilike` khi gợi ý tên hàng nhập tay.
     - **M1 (Stored Count)**: Bổ sung `store=True` cho trường `zalo_message_count` trên `pos.order` để tăng tốc độ load view danh sách đơn hàng POS.
     - **Sửa nhanh NameError Controller**: Bổ sung import `UserError` trong `qba_ai/controllers/main.py`.
  3. Kiểm tra biên dịch và khởi động lại container Odoo thành công, hệ thống hoạt động ổn định.
- **File đã thay đổi:**
  - `odoo/custom_addons/qba_pos/models/pos_order.py`
  - `odoo/custom_addons/qba_pos/models/product_template.py`
  - `odoo/custom_addons/qba_pos/models/pos_custom_product_history.py`
  - `odoo/custom_addons/qba_ai/controllers/main.py`
  - `SESSION_STATE.md`

---

## 5. Việc Cần Làm Tiếp Theo (Backlog / Pending Tasks)

- [x] Khởi tạo nhánh `perf-optimize-qba-core` và hoàn thành tối ưu module lõi `qba` ✅
- [x] Khởi tạo nhánh `perf-optimize-qba-ai` và hoàn thành tối ưu module `qba_ai` ✅
- [x] Khởi tạo nhánh `perf-optimize-qba-pos` và hoàn thành tối ưu module `qba_pos` ✅
- [ ] Commit nhánh `perf-optimize-qba-pos`.
- [ ] Nghiệm thu toàn diện cả 3 module trên giao diện Odoo.
- [ ] Hợp nhất (Merge) các nhánh tối ưu vào nhánh chính theo yêu cầu người dùng.
