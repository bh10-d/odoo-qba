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

- **Thời gian:** 2026-11-07 23:40 (GMT+7)
- **Nhánh Git:** `feature/admin-product-management`
- **Công việc đã hoàn thành:**
  1. **Audit & Gia Cố Toàn Diện Luồng Tiền Tệ Chiết Khấu Mua Hàng (`purchase.order.line`):**
     - **Phát hiện & xử lý rủi ro Định giá tồn kho (Inventory Valuation):** Odoo standard `purchase_stock` khi tạo dịch chuyển kho (`stock.move`) dùng đơn giá gốc chưa trừ chiết khấu (`self.price_unit`), khiến giá trị kho bị ghi nhận cao hơn thực tế và lệch tài khoản trung gian nhập kho (`Stock Interim Received`). Đã override `_get_stock_move_price_unit()` áp dụng đúng tỷ lệ giảm giá sang `stock.move` (`83,333.33đ/cái`), triệt tiêu 100% rủi ro lệch định giá tài sản và giá vốn hàng bán (COGS).
     - **Thêm ràng buộc kiểm soát rủi ro tài chính (`@api.constrains`):**
       - Chặn hoàn toàn số tiền chiết khấu âm (`discount_amount < 0`).
       - Chặn tỷ lệ chiết khấu ngoài khoảng `[0%, 100%]`.
       - Chặn số tiền chiết khấu vượt quá tổng tiền hàng của dòng (`discount_amount > abs(price_unit * qty)`).
     - **Hỗ trợ an toàn dòng trả hàng (Số lượng âm):** Dùng `abs(self.product_qty)` trong các phép tính đơn giá và tỷ lệ chiết khấu, ngăn chặn lỗi đảo dấu tiền tệ khi xuất trả hàng nhà cung cấp.
     - **Bộ Test Kiểm Toán 5/5 Đạt 100%:**
       - Test 1: Đơn mua và đơn giá nhập kho `stock.move` tính chính xác `83,333.33đ`.
       - Test 2: Bắt lỗi nhập tiền chiết khấu âm.
       - Test 3: Bắt lỗi chiết khấu vượt quá tiền hàng.
       - Test 4: Bắt lỗi tỷ lệ chiết khấu > 100%.
       - Test 5: Xác nhận đơn -> Nhập kho -> Lập Hóa đơn NCC (`account.move.line`) khớp số tiền `250,000đ` tuyệt đối.
  2. **Thêm Cột Tiền Chiết Khấu Bằng Số (`CK`) Trên Đơn Mua Hàng:**
     - Đã thêm trường `discount_amount` (Monetary, ký hiệu / nhãn **`CK`**) song hành cùng `% CK` (`discount`) trên chi tiết đơn mua hàng, hỗ trợ đồng bộ hai chiều và hiển thị trên list/form/kanban view.
  3. **Tự Động Tính Số Lượng Hiện Có & Dự Báo (SL hiện có = Đã nhập - Đã bán):**
     - Đã hoàn tất và đồng bộ CSDL.
  4. Đã nâng cấp module `qba` (`odoo-bin -u qba`) và khởi động lại container Odoo `staging-qba-odoo-1` hoạt động ổn định (HTTP 200).
- **File đã thay đổi / tạo mới:**
  - `odoo/custom_addons/qba/models/purchase_order_line.py` (Mới - Override `purchase.order.line`)
  - `odoo/custom_addons/qba/models/__init__.py` (Import `purchase_order_line`)
  - `odoo/custom_addons/qba/views/purchase_order_views.xml` (Mới - Thêm cột `CK` & `% CK` vào form Mua hàng)
  - `odoo/custom_addons/qba/__manifest__.py` (Đăng ký `purchase_order_views.xml`)
  - `SESSION_STATE.md` (Cập nhật bàn giao)

---

## 5. Việc Cần Làm Tiếp Theo (Backlog / Pending Tasks)

- [x] Khắc phục lỗi xuất Hóa đơn POS `deferred_start_date` ✅
- [x] Khắc phục lỗi `Cursor already closed` và kiểm thử Trợ lý QBA AI ✅
- [x] Nâng cấp Showcase Card ảnh sản phẩm trên `product.template` form view ✅
- [x] Fix thao tác kéo rê pan ảnh khi phóng to trong Lightbox ✅
- [x] Fix bug UI 2 checkbox Điểm bán hàng trên trang thông tin sản phẩm ✅
- [x] Chuẩn hóa 4 Tab Xe, Động cơ, Hộp số, Cầu hiển thị phân cấp từ gốc đến ngọn như Danh mục ✅
- [x] Bật hiển thị trực tiếp cột Nhãn hiệu & Chủng loại trên các bảng danh mục Hộp số, Động cơ, Xe, Cầu ✅
- [x] Tự động tính số lượng hiện có theo lịch sử Mua/Bán khi bật theo dõi tồn kho ✅
- [x] Thêm cột tiền chiết khấu bằng số `CK` bên cạnh `% CK` trên đơn mua hàng ✅
- [x] Người dùng kiểm tra giao diện trên trình duyệt (`http://localhost:8089`) ✅
- [x] Commit và push các thay đổi lên nhánh `feature/admin-product-management` ✅
