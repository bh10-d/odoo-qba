# Project Session State & Handover

Tài liệu này lưu trữ trạng thái làm việc và nhật ký bàn giao giữa các phiên làm việc (chat sessions).
**Mỗi phiên làm việc mới BẮT ĐẦU bằng việc đọc file này và KẾT THÚC bằng việc cập nhật file này.**

---

## 1. Thông Tin Môi Trường & Kiến Trúc Hiện Tại (Baseline)

- **Dự án:** QBA Odoo 18 Community (Phụ tùng ô tô xe tải nặng Q.BA)
- **Nhánh Git hiện tại:** `perf-optimize-qba-core`
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

- **Thời gian:** 2026-11-06 15:45 (GMT+7)
- **Nhánh Git:** `perf-optimize-qba-core`
- **Công việc đã hoàn thành:**
  1. Tạo và checkout nhánh mới `perf-optimize-qba-core` để tối ưu toàn diện module lõi `qba`.
  2. **Giải quyết triệt để HIGH 1 (N+1 Tree View trên 4 danh mục phụ tùng)**:
     - Refactor `_compute_product_count` trong [`axle.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/axle.py), [`engine.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/engine.py), [`gearbox.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/gearbox.py), [`vehicle.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/vehicle.py).
     - Gom nhóm đếm sản phẩm bằng 1 truy vấn SQL `GROUP BY` trực tiếp vào bảng quan hệ Many2many (`product_vehicle_rel`, `product_engine_rel`, `product_gearbox_rel`, `product_axle_rel`) thay vì chạy `search_count` vòng lặp $2 \times N$ lần.
  3. **Giải quyết triệt để HIGH 2 (HTTP Sync Blocking trong DB Transaction)**:
     - Refactor `write()` trong [`product_template.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_template.py): bọc lệnh gọi `_notify_express_unlink` và `_notify_express_update_display` vào post-commit hook `self.env.cr.after('commit', ...)`.
     - Loại bỏ hoàn toàn nguy cơ treo khóa dòng PostgreSQL khi kết nối Backend Express.js bị chậm.
  4. **Giải quyết triệt để HIGH 3 (Vòng lặp N+1 `stock.move` trong Bulk Edit Wizard)**:
     - Refactor khóa an toàn kiểm tra ĐVT trong [`product_bulk_edit_wizard.py`](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba/models/product_bulk_edit_wizard.py).
     - Batch toàn bộ `variant_ids` vào 1 câu SQL `SELECT DISTINCT product_id FROM stock_move WHERE product_id IN %s`, loại bỏ hoàn toàn N queries.
  5. Kiểm tra syntax bằng `py_compile` và khởi động lại container Odoo thành công, hệ thống hoạt động ổn định.
- **File đã thay đổi:**
  - `odoo/custom_addons/qba/models/axle.py`
  - `odoo/custom_addons/qba/models/engine.py`
  - `odoo/custom_addons/qba/models/gearbox.py`
  - `odoo/custom_addons/qba/models/vehicle.py`
  - `odoo/custom_addons/qba/models/product_template.py`
  - `odoo/custom_addons/qba/models/product_bulk_edit_wizard.py`
  - `SESSION_STATE.md`

---

## 5. Việc Cần Làm Tiếp Theo (Backlog / Pending Tasks)

- [x] Khởi tạo nhánh `perf-optimize-qba-core` và hoàn thành tối ưu module lõi `qba` ✅
- [ ] Kiểm tra thực tế trên giao diện Odoo (Danh mục xe/động cơ/hộp số, sửa hàng loạt, đồng bộ web).
- [ ] Commit nhánh `perf-optimize-qba-core` sau khi người dùng nghiệm thu.
- [ ] Chuyển sang module tiếp theo: Tạo nhánh `perf-optimize-qba-ai` để xử lý các mục trong `qba_ai` (H4, H5, H6, H7, M3, M4, M5, M6, M7, L1, L2).
- [ ] Cuối cùng: Tạo nhánh `perf-optimize-qba-pos` để xử lý các mục trong `qba_pos` (H1, H2, H3, M1, M2).
