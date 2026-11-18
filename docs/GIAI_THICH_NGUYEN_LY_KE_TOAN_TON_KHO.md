# Giải Thích Nguyên Lý Kế Toán & Quy Trình Xử Lý Tồn Kho Quá Khứ Trên Odoo 18

Tài liệu này giải thích rõ **bản chất kế toán** của vấn đề tồn kho khi chuyển sản phẩm từ trạng thái *Chưa theo dõi tồn kho* sang *Theo dõi hàng tồn kho*, lý do khóa quyền sửa tay, và cách hệ thống xử lý để sổ sách luôn khớp đúng thực tế.

---

## 1. Vì sao Odoo mặc định khóa không cho bật lại "Theo dõi hàng tồn kho" & không có số tồn cũ?

Trong Odoo, một sản phẩm có 2 tính chất hoàn toàn khác nhau:
1. **Không theo dõi tồn kho (`is_storable = False`):** Odoo chỉ ghi nhận **chứng từ thương mại** (Đơn mua PO → tab *Đã mua*, Đơn bán SO/POS → tab *Đã bán*) và **không sinh phiếu nhập/xuất kho (`stock.move`)** cũng như **không ghi sổ tồn kho (`stock.quant`)**.
2. **Có theo dõi tồn kho (`is_storable = True`):** Mọi giao dịch mua/bán đều phải đi qua **Phiếu nhập kho (`WH/IN`)** và **Phiếu xuất kho (`WH/OUT`)** để tăng/giảm số lượng tồn thực tế và hạch toán giá trị hàng tồn kho.

**Hệ quả khi quên tick "Theo dõi hàng tồn kho" từ đầu:**
- Các toa mua 48 cái hay bán 2 cái trước đây chỉ nằm ở lịch sử mua/bán, chưa từng đi vào sổ kho.
- Khi bật lại theo dõi kho, Odoo không tự cộng ngược quá khứ nên số **Hiện có = 0**.
- Theo đúng nguyên lý kế toán chuẩn của Odoo, Odoo **khóa cứng** trường này sau khi đã có giao dịch phát sinh để tránh tình trạng tồn kho và giá trị kho bị lệch giữa sổ thương mại và sổ kho.

---

## 2. Tại sao KHÔNG cho nhân viên sửa tay trực tiếp và KHÔNG tạo đơn Mua/Bán giả?

### ❌ Rủi ro nếu để nhân viên dùng nút "Cập nhật số lượng" tùy tiện
- Nút **Cập nhật số lượng** là công cụ điều chỉnh trực tiếp vào sổ kho mà **không cần chứng từ mua/bán đối ứng**.
- Nếu nhân viên tự ý gõ số vào (ví dụ: trước đây đã mua 48 cái lúc chưa bật kho, nay lại bấm cập nhật thêm 48 cái nữa nhưng không đối trừ số đã bán, hoặc mua thêm lần nữa thành **96 cái khống**), sổ sách sẽ **sai lệch hoàn toàn** và không truy vết được nguyên nhân tăng/giảm kho.
- **Giải pháp đã áp dụng:** Bỏ hoàn toàn nút **Cập nhật số lượng** (và nút **Tính Tồn Kho Theo Mua/Bán**) khỏi form Sản phẩm. Khi bấm vào ô *Hiện có* trên form sản phẩm, mọi người chỉ xem được chi tiết vị trí kho ở chế độ **chỉ đọc**. Trường hợp cần điều chỉnh kiểm kê cuối kỳ (hàng mất, vỡ hỏng), Kế toán/Admin thực hiện đúng quy trình tại menu **Tồn kho → Hoạt động → Kiểm kê thực tế**.

### ❌ Rủi ro nếu dùng mẹo "Tạo đơn bán 48 cái về 0 → bật kho → Tạo đơn mua lại 48 cái"
- Mặc dù đi qua đơn hàng, nhưng **tạo đơn bán giả + đơn mua giả** sẽ làm:
  1. **Nhân đôi ảo số liệu `Đã mua` và `Đã bán`** (từ 48 cái thành 96 cái).
  2. **Sai lệch báo cáo Doanh thu, Công nợ phải thu/phải trả** và **Lịch sử giá nhập hàng** thực tế của nhà cung cấp.

---

## 3. Phương án chuẩn kế toán đang áp dụng: Bút toán Khai báo Tồn đầu kỳ

Thay vì sửa tay bừa bãi hoặc tạo đơn mua/bán giả, hệ thống áp dụng đúng nguyên lý **Khai báo Tồn kho Đầu kỳ (Opening Inventory Adjustment)**:

1. **Thời điểm thực hiện (chỉ chạy đúng 1 lần khi bật theo dõi kho `False → True`):**
   - Hệ thống tự động truy xuất lịch sử thực tế của mã hàng:
     $$\text{Tồn đầu kỳ} = \max\left(0,\; \text{Tổng Đã Mua} - \text{Tổng Đã Bán}\right)$$
   - Trong đó:
     - **Tổng Đã Mua:** Lấy từ các đơn mua hàng đã xác nhận/hoàn tất (`purchase`, `done`) hoặc phiếu nhập kho đã hoàn tất (`done`).
     - **Tổng Đã Bán:** Lấy từ đơn bán hàng (`sale`, `done`), đơn POS (đã thanh toán/hoàn tất, loại trừ nháp/hủy) hoặc phiếu xuất kho đã hoàn tất (`done`).
   - *Ví dụ:* Đã mua **48**, đã bán **2** → Hệ thống ghi nhận tồn đầu kỳ = **46**.

2. **Chứng từ kế toán & Truy vết (Audit Trail):**
   - Hệ thống không sửa số thô trong database mà gọi chuẩn `_apply_inventory()` của Odoo, tự động sinh ra **1 dịch chuyển kho kiểm kê đầu kỳ** từ `Kho ảo / Điều chỉnh kiểm kê (Virtual Locations/Inventory adjustment)` → `WH/Tồn kho` với diễn giải **"Tồn đầu kỳ theo lịch sử Mua/Bán"**.
   - Đồng thời ghi chú trực tiếp vào **Chatter** của sản phẩm:
     > *"Khai báo tồn kho đầu kỳ khi bật Theo dõi hàng tồn kho: Đã mua X - Đã bán Y → Tồn đầu kỳ = Z."*

3. **Vận hành từ thời điểm sau khi đã bật theo dõi kho:**
   - Hệ thống **không bao giờ tự động ghi đè lại** số lượng của các mã đang theo dõi kho bình thường.
   - Mọi biến động tăng/giảm tồn kho hằng ngày bắt buộc đi qua **Phiếu nhập kho (từ Đơn mua hàng PO)** và **Phiếu xuất kho (từ Đơn bán hàng SO / POS)** đúng chuẩn kế toán.

---

## 4. Tóm tắt quy trình kiểm tra thực tế (Test)

1. Mở 1 sản phẩm trong nhóm chưa bật theo dõi kho (hiện có **67 mã** giữ nguyên để test tay).
2. Kiểm tra số **Đã mua** và **Đã bán** hiện tại của sản phẩm.
3. Dùng tài khoản **Admin** tick bật **"Theo dõi hàng tồn kho"** và Lưu.
4. Kiểm tra kết quả:
   - Ô **Hiện có** và **Được dự báo** tự động cập nhật đúng bằng `Đã mua - Đã bán`.
   - Tab **Lịch sử kho** có 1 bút toán đầu kỳ *"Tồn đầu kỳ theo lịch sử Mua/Bán"*.
   - **Chatter** bên phải có dòng log đối chiếu rõ số Đã mua / Đã bán / Tồn đầu kỳ.
   - Trên form sản phẩm không còn nút **Cập nhật số lượng**, và khi bấm vào ô **Hiện có** chỉ xem được tồn kho ở chế độ chỉ đọc.
