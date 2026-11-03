# TÀI LIỆU HƯỚNG DẪN SỬ DỤNG PHÂN HỆ ĐIỂM BÁN HÀNG QBA (USER MANUAL)
## QUẢN LÝ BÁN LẺ, BÁN HÀNG CHƯA CÓ TRONG KHO & BẢO HÀNH ZALO

* **Dành cho:** Nhân viên Thu ngân, Nhân viên Bán lẻ tại quầy, Kế toán Bán hàng và Quản lý Cửa hàng
* **Hệ thống:** Phân hệ `qba_pos` trên nền tảng Odoo 18 Community Edition
* **Chuyên ngành:** Phụ tùng xe tải hạng nặng (HOWO, SHACMAN, CHENGLONG, v.v.)
* **Tài liệu kiểm toán đính kèm:** [AUDIT_REPORT.md](file:///e:/hoctap/Language/Python/qba-odoo/staging-qba-odoo/odoo/custom_addons/qba_pos/doc/AUDIT_REPORT.md)
* **Ngày phát hành:** 30/10/2026

---

## MỤC LỤC
1. [GIỚI THIỆU TỔNG QUAN](#1-giới-thiệu-tổng-quan)
2. [CÁC QUY TẮC AN TOÀN VẬN HÀNH BẮT BUỘC](#2-các-quy-tắc-an-toàn-vận-hành-bắt-buộc)
3. [QUY TRÌNH 1: MỞ CA VÀ THIẾT LẬP PHIÊN BÁN HÀNG](#3-quy-trình-1-mở-ca-và-thiết-lập-phiên-bán-hàng)
4. [QUY TRÌNH 2: BÁN HÀNG CÓ SẴN TRONG KHO ODOO](#4-quy-trình-2-bán-hàng-có-sẵn-trong-kho-odoo)
5. [QUY TRÌNH 3: BÁN HÀNG CHƯA CÓ TRONG KHO (SP_CHUA_CO_MA)](#5-quy-trình-3-bán-hàng-chưa-có-trong-kho-sp_chua_co_ma)
   - 5.1. Khi nào sử dụng tính năng này?
   - 5.2. Các bước nhập hàng và sử dụng gợi ý Autocomplete
   - 5.3. Cơ chế học tự động của hệ thống
   - 5.4. Thể hiện trên hóa đơn in bill và công nợ
6. [QUY TRÌNH 4: THANH TOÁN VÀ XỬ LÝ CÔNG NỢ](#6-quy-trình-4-thanh-toán-và-xử-lý-công-nợ)
   - 6.1. Thanh toán Tiền Mặt
   - 6.2. Thanh toán Chuyển Khoản Ngân Hàng
   - 6.3. Bán chịu / Ghi sổ Công nợ khách hàng
7. [QUY TRÌNH 5: BẢO HÀNH VÀ TIN NHẮN ZALO CSKH](#7-quy-trình-5-bảo-hành-và-tin-nhắn-zalo-cskh)
   - 7.1. Cơ chế gửi tin bảo hành tự động
   - 7.2. Tra cứu lịch sử và gửi lại tin nhắn khi cần
8. [QUY TRÌNH 6: QUẢN TRỊ VIÊN ĐỒNG BỘ DỮ LIỆU & ĐÓNG PHIÊN](#8-quy-trình-6-quản-trị-viên-đồng-bộ-dữ-liệu--đóng-phiên)
   - 8.1. Đồng bộ sản phẩm và danh mục POS
   - 8.2. Quản lý từ điển tên hàng nhập tay
   - 8.3. Đóng ca và đối soát cuối ngày
9. [XỬ LÝ CÁC SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)](#9-xử-lý-các-sự-cố-thường-gặp-troubleshooting)

---

## 1. GIỚI THIỆU TỔNG QUAN

Phân hệ **QBA POS** được thiết kế chuyên biệt cho hoạt động kinh doanh bán lẻ và bán buôn phụ tùng xe tải tại quầy của Phụ tùng ô tô Q.BA:
- **Tốc độ xử lý tức thì:** Nạp hơn 3.000 phụ tùng chỉ trong 3.5 giây, tìm kiếm nhanh và mượt mà không có độ trễ.
- **Bán hàng linh hoạt:** Cho phép bán cả sản phẩm đã số hóa trong kho và sản phẩm phát sinh thực tế chưa có mã trên phần mềm (`SP_CHUA_CO_MA`).
- **Ghi nhớ thông minh:** Tự động lưu vết và gợi ý tên phụ tùng nhập tay từ lịch sử bán hàng theo ký tự gần đúng (Autocomplete), giúp thu ngân không phải gõ lại nhiều lần.
- **Bảo toàn kho và công nợ kế toán:** Không sinh ra tồn kho âm khi bán hàng ngoài danh mục, nhưng vẫn phản ánh chính xác 100% doanh thu và công nợ của từng khách hàng.
- **Tự động hóa CSKH:** Gửi xác nhận đơn hàng và điều khoản bảo hành chi tiết tới Zalo của khách hàng ngay khi thanh toán.

---

## 2. CÁC QUY TẮC AN TOÀN VẬN HÀNH BẮT BUỘC

> [!CAUTION]
> **Nhân viên thu ngân và bán hàng tại quầy bắt buộc phải ghi nhớ 3 nguyên tắc sau:**

1. **Bắt buộc chọn thông tin Khách hàng khi bán chịu (Ghi nợ):**  
   Khi khách hàng mua nợ phụ tùng, thu ngân bắt buộc phải chọn hoặc tạo mới hồ sơ Khách hàng trên giao diện POS trước khi xác nhận phương thức *Công Nợ Khách Hàng (Ghi Sổ)*. Nếu không chọn khách hàng, hệ thống sẽ ngăn chặn thanh toán để tránh công nợ bị ghi nhận vô danh.
2. **Cập nhật số điện thoại chính xác để nhận bảo hành Zalo:**  
   Để tin nhắn bảo hành tự động được chuyển tới tài khoản Zalo của khách, hồ sơ khách hàng phải có số điện thoại di động hợp lệ (định dạng 10 số, ví dụ: `0905123456`).
3. **Phân biệt hàng nhập tay và hàng có sẵn:**  
   Chỉ sử dụng nút *SP Nhap Tay* cho các phụ tùng thực sự chưa được nhập mã vào Odoo (hàng mới về đột xuất, hàng gia công thêm, hàng lấy hộ). Đối với các sản phẩm đã có sẵn mã trong kho, thu ngân phải tìm kiếm đúng mã SKU hoặc quét mã vạch để hệ thống quản lý chính xác tồn kho thực tế.

---

## 3. QUY TRÌNH 1: MỞ CA VÀ THIẾT LẬP PHIÊN BÁN HÀNG

1. **Truy cập Điểm bán hàng:**
   * Từ menu chính của Odoo, nhấp chuột vào biểu tượng **Điểm bán hàng (Point of Sale)**.
2. **Mở phiên làm việc:**
   * Tại thẻ máy bán hàng **`POS Ban Le Q.BA`**, bấm nút **Mở Phiên (New Session)**.
   * Chờ hệ thống đồng bộ dữ liệu sản phẩm trong khoảng 3 đến 4 giây.
3. **Khai báo số dư tiền mặt đầu ca:**
   * Nếu có tiền mặt tồn đầu ca để thối lại cho khách, thu ngân nhập số tiền vào ô **Kiểm soát tiền mặt đầu ca (Opening Cash Control)**, sau đó bấm **Mở ca bán hàng (Open Session)**.

---

## 4. QUY TRÌNH 2: BÁN HÀNG CÓ SẴN TRONG KHO ODOO

1. **Tìm kiếm sản phẩm:**
   * **Cách 1: Gõ từ khóa vào thanh tìm kiếm:** Nhập mã phụ tùng (SKU), mã quy cách hoặc tên phụ tùng (hỗ trợ gõ tiếng Việt có dấu hoặc không dấu, ví dụ: `loc dau howo`, `la con 430`, `bodi`).
   * **Cách 2: Chọn theo Danh mục (Tabs):** Bấm chọn danh mục phụ tùng ở phía trên màn hình (Động cơ, Gầm - Cầu, Thân vỏ, Côn - Hộp số...) để lọc nhanh nhóm sản phẩm.
   * **Cách 3: Sử dụng máy quét mã vạch:** Quét trực tiếp mã vạch trên bao bì phụ tùng.
2. **Thêm sản phẩm vào giỏ hàng:**
   * Bấm vào hình ảnh hoặc dòng sản phẩm để đưa vào đơn hàng.
   * Bấm liên tiếp để tăng số lượng, hoặc bấm vào nút số lượng (`Số lượng / Qty`) trên bàn phím số để nhập số lượng mong muốn.
3. **Điều chỉnh giá hoặc chiết khấu (nếu được phép):**
   * Bấm nút **Giá bán (Price)** để điều chỉnh đơn giá bán lẻ theo thỏa thuận.
   * Bấm nút **% Chiết khấu (% Disc)** để nhập tỷ lệ giảm giá cho khách hàng thân thiết.

---

## 5. QUY TRÌNH 3: BÁN HÀNG CHƯA CÓ TRONG KHO (SP_CHUA_CO_MA)

Đây là tính năng độc quyền giải quyết dứt điểm tình trạng phụ tùng thực tế có tại cửa hàng hoặc lấy từ nguồn ngoài giao gấp cho khách nhưng chưa kịp tạo mã trong phần mềm.

### 5.1. Khi nào sử dụng tính năng này?
* Khách lấy phụ tùng mới nhập về cửa hàng trong ngày, thủ kho chưa kịp cập nhật danh mục SKU lên Odoo.
* Hàng phụ tùng hiếm lấy hộ từ đơn vị liên kết để giao kèm đơn cho khách.
* Dịch vụ sửa chữa, hàn tiện, ép tuy-ô phát sinh kèm theo phụ tùng.

### 5.2. Các bước nhập hàng và sử dụng gợi ý Autocomplete

1. **Kích hoạt tính năng:**
   * Bấm vào nút màu vàng nổi bật **"SP Nhap Tay"** nằm ngay phía trên bàn phím điều khiển POS.
   * *(Hoặc gõ từ khóa `SP_CHUA_CO_MA` vào ô tìm kiếm sản phẩm).*
2. **Thao tác trên cửa sổ nhập hàng:**
   * Cửa sổ **"Nhap Hang Chua Co Ma [Nhap Tay]"** sẽ mở ra và con trỏ tự động đặt tại ô tên hàng.
   * **Gõ tên phụ tùng:** Bắt đầu gõ vài ký tự của tên phụ tùng (ví dụ: gõ `loc nhot`, `tuy o`, `chot nhiep`...).
   * **Gợi ý tự động (Autocomplete):**
     * Hệ thống lập tức hiển thị danh sách các tên hàng tương tự đã từng bán trước đây.
     * Mỗi dòng gợi ý thể hiện rõ: Tên hàng, Đơn giá gần nhất đã bán, và Số lần đã sử dụng trong lịch sử.
     * Sử dụng phím **Mũi tên Xuống (Down Arrow)** và **Mũi tên Lên (Up Arrow)** trên bàn phím để di chuyển chọn mặt hàng phù hợp.
     * Bấm phím **Enter** để chọn dòng gợi ý. Hệ thống sẽ tự động điền tên và tự động điền đơn giá bán gần nhất vào ô Đơn giá.
   * **Nhập Số lượng & Đơn giá bán:**
     * Nhập số lượng thực tế khách mua.
     * Điều chỉnh đơn giá bán nếu giá đợt này thay đổi.
   * **Nhập Ghi chú / Quy cách (Tùy chọn):**
     * Điền thông số chi tiết của phụ tùng (ví dụ: *Hàng 8 lò xo, lỗ then hoa 10 răng, cốt 50mm*).
3. **Xác nhận thêm vào đơn:**
   * Bấm nút **"Thao Tác / Them Vao Don"** (hoặc nhấn phím **Enter** khi đang ở ô tên hàng).
   * Dòng hàng sẽ xuất hiện trong giỏ hàng với huy hiệu màu vàng nhận diện: `[Nhap tay]`.

### 5.3. Cơ chế học tự động của hệ thống
* Nếu đây là một tên phụ tùng hoàn toàn mới, hệ thống sẽ tự động lưu tên này vào từ điển gợi ý cho các lần bán tiếp theo.
* Nếu là tên đã có, hệ thống tự động tăng biến đếm số lần sử dụng (`use_count + 1`) và cập nhật đơn giá mới nhất. Các phụ tùng bán càng nhiều lần sẽ càng được ưu tiên đẩy lên đầu danh sách gợi ý.

### 5.4. Thể hiện trên hóa đơn in bill và công nợ
* **Trên hóa đơn in bill cho khách:** Dòng hàng in chính xác tên thực tế do thu ngân nhập (ví dụ: `Lọc nhớt Howo A7 371HP x 2 (560.000 d)`), không in chữ chung chung `SP_CHUA_CO_MA`.
* **Trên hệ thống kế toán:** Dòng hàng này ghi nhận doanh thu và hạch toán đúng số tiền nợ vào sổ chi tiết khách hàng, đồng thời không tạo lệnh trừ kho nên không làm âm kho hàng.

---

## 6. QUY TRÌNH 4: THANH TOÁN VÀ XỬ LÝ CÔNG NỢ

Sau khi hoàn tất việc thêm các mặt hàng vào giỏ hàng:
1. Bấm nút màu xanh **Thanh toán (Payment)** ở góc dưới bên phải màn hình.
2. **Chọn Khách hàng:** Bấm nút **Khách hàng (Customer)** ở phía trên bên trái:
   * Tìm kiếm tên hoặc số điện thoại của nhà xe, xưởng sửa chữa, tài xế.
   * Nếu là khách hàng mới: Bấm **Tạo mới (Create)**, điền Tên và Số điện thoại di động, sau đó bấm **Lưu & Đặt khách hàng**.
3. **Lựa chọn phương thức thanh toán:**

### 6.1. Thanh toán Tiền Mặt
* Bấm chọn nút **Tiền Mặt (Cash)**.
* Nhập số tiền khách đưa bằng bàn phím số bên phải.
* Hệ thống tự động tính số tiền thừa thối lại cho khách.

### 6.2. Thanh toán Chuyển Khoản Ngân Hàng
* Bấm chọn nút **Chuyen Khoan Ngan Hang (Bank)**.
* Hướng dẫn khách hàng quét mã QR chuyển khoản đúng số tiền hiển thị trên màn hình.
* Khi tài khoản ngân hàng thông báo nhận tiền thành công, thu ngân bấm tiếp tục.

### 6.3. Bán chịu / Ghi sổ Công nợ khách hàng
* Bấm chọn nút **Cong No Khach Hang (Ghi So)**.
* Hệ thống tự động gán toàn bộ số tiền đơn hàng vào tài khoản phải thu công nợ của khách hàng đã chọn.
* *(Lưu ý: Nếu chưa chọn khách hàng, hệ thống sẽ cảnh báo yêu cầu chọn khách hàng trước).*

4. **Xác nhận đơn hàng và in bill:**
   * Bấm nút lớn **Xác nhận (Validate)**.
   * Phiếu bán lẻ (Bill) tự động được in ra từ máy in hóa đơn.
   * Đưa bill cho khách hàng và hoàn tất đơn hàng.
   * Bấm **Đơn hàng mới (New Order)** để phục vụ khách tiếp theo.

---

## 7. QUY TRÌNH 5: BẢO HÀNH VÀ TIN NHẮN ZALO CSKH

### 7.1. Cơ chế gửi tin bảo hành tự động
* Ngay sau khi bấm nút **Xác nhận (Validate)** thanh toán đơn hàng thành công, hệ thống tự động kiểm tra số điện thoại của khách hàng.
* Nếu khách hàng có số điện thoại, hệ thống sẽ tự động tạo một tin nhắn bảo hành điện tử và gửi tới Zalo của khách hàng.
* **Cấu trúc tin nhắn Zalo gửi khách hàng:**
  ```text
  PHU TUNG O TO Q.BA - XAC NHAN DON HANG & BAO HANH
  Kinh chao: Cong ty Van Tai Hoang Long
  Ma don: POS/2026/10/30/0008 - Ngay: 30/10/2026

  DANH SACH PHU TUNG:
  1. Loc dau Howo A7 x 2 (560,000 d)
  2. Bop con Howo 371 x 1 (1,250,000 d)
  3. Tuy-o dau hoi cao ap 1.2m [Nhap tay] x 1 (350,000 d)
  Tong thanh toan: 2,160,000 d

  CHINH SACH BAO HANH:
  Bao hanh theo tieu chuan nha san xuat. Doi tra trong 7 ngay neu con nguyen tem.

  Hotline ho tro / Bao hanh: 0905.123.456
  Xin chan thanh cam on Quy khach!
  ```

### 7.2. Tra cứu lịch sử và gửi lại tin nhắn khi cần
1. Từ màn hình quản trị Odoo, vào menu **Điểm bán hàng > Đơn hàng > Đơn hàng**.
2. Mở đơn hàng POS tương ứng.
3. Ở phía trên đầu đơn hàng có nút thông minh **Tin Nhắn Zalo**:
   * Nhấp vào nút này để xem trạng thái gửi tin (`Da Gui Thanh Cong`, `Mo Phong Thanh Cong`, hoặc `Gui That Bai`).
   * Xem nội dung tin nhắn và thời gian gửi chính xác.
4. Nếu khách báo chưa nhận được tin nhắn (do mất mạng tạm thời lúc bán hàng):
   * Mở bản ghi tin nhắn Zalo đó, kiểm tra lại số điện thoại và bấm nút **Gửi Lại Tin Nhắn (Resend)**.

---

## 8. QUY TRÌNH 6: QUẢN TRỊ VIÊN ĐỒNG BỘ DỮ LIỆU & ĐÓNG PHIÊN

### 8.1. Đồng bộ sản phẩm và danh mục POS
Khi cửa hàng nhập thêm nhiều mã phụ tùng mới vào phần mềm hoặc cơ cấu lại danh mục cây sản phẩm:
1. Vào menu **Điểm bán hàng > Cấu hình > Thiết lập (Settings)**.
2. Tìm tới nhóm cấu hình **Quản Lý & Tối Ưu Danh Mục Sản Phẩm POS**:
   * Bấm nút **"Bật Bán Trên POS Cho Tất Cả Sản Phẩm"**: Hệ thống sẽ tự động quét và kích hoạt tính năng bán hàng POS cho toàn bộ phụ tùng mới.
   * Bấm nút **"Đồng Bộ Danh Mục Sang POS"**: Hệ thống sẽ tự động đồng bộ toàn bộ 218 danh mục phụ tùng xe tải sang hệ thống tab danh mục trên POS.

### 8.2. Quản lý từ điển tên hàng nhập tay
Để kiểm tra, chuẩn hóa hoặc dọn dẹp các tên hàng do thu ngân tự gõ:
1. Vào menu **Điểm bán hàng > Sản phẩm > Lịch Sử Tên SP Nhập Tay**.
2. Giao diện hiển thị danh sách toàn bộ các tên hàng đã từng bán kèm:
   * **Số lần đã sử dụng:** Cho biết mặt hàng nào được bán nhập tay thường xuyên nhất.
   * **Đơn giá gần nhất:** Có thể điều chỉnh lại giá chuẩn để các lần gợi ý sau chính xác hơn.
3. *Khuyến nghị:* Những mặt hàng nhập tay có số lần sử dụng cao (trên 10 lần) nên được chuyển giao cho thủ kho để tạo mã SKU chính thức đưa vào danh mục kho Odoo.

### 8.3. Đóng ca và đối soát cuối ngày
1. Trên giao diện POS, bấm nút **Đóng (Close)** ở góc trên bên phải màn hình.
2. Kiểm đếm tiền mặt thực tế trong két và nhập vào ô **Tiền mặt thực tế (Counted Cash)**.
3. Xem bảng đối chiếu tổng tiền mặt, tổng chuyển khoản ngân hàng và tổng công nợ phát sinh trong ca.
4. Bấm nút **Đóng phiên & Đăng sổ bút toán (Close Session & Post Entries)** để kế toán ghi nhận sổ cái.

---

## 9. XỬ LÝ CÁC SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

| Hiện tượng sự cố | Nguyên nhân | Hướng dẫn xử lý |
| :--- | :--- | :--- |
| **Bấm thanh toán Công nợ bị báo lỗi hoặc không chọn được** | Chưa chọn Khách hàng trên giao diện đơn hàng POS. | Bấm vào ô **Khách hàng** ở góc trên bên trái, chọn đối tác cụ thể rồi quay lại bấm thanh toán. |
| **Khách hàng không nhận được tin nhắn Zalo** | 1. Hồ sơ khách hàng bị thiếu số điện thoại di động.<br>2. Hệ thống đang để chế độ Mô phỏng (Simulation).<br>3. Mất kết nối internet lúc thanh toán. | 1. Bổ sung số điện thoại trong hồ sơ khách.<br>2. Kiểm tra trong **Thiết lập POS**: nếu cần gửi thật phải chuyển sang Chế độ Chính thức và nhập Access Token.<br>3. Vào đơn hàng POS trong Backend và bấm nút **Gửi Lại Tin Nhắn**. |
| **Không tìm thấy phụ tùng nhập tay trong danh sách gợi ý** | Từ khóa gõ chưa từng được bán trước đây. | Cứ tiếp tục gõ trọn vẹn tên hàng lần đầu tiên. Hệ thống sẽ tự động ghi nhớ và gợi ý cho tất cả các lần bán sau. |
| **Máy in không tự động in hóa đơn sau khi thanh toán** | Trình duyệt chặn cửa sổ popup in ấn hoặc máy in bị ngắt kết nối. | Kiểm tra dây cáp/kết nối mạng của máy in bill. Cho phép trình duyệt mở popup in ấn mặc định. Tại màn hình biên lai POS, bấm nút **In biên lai (Print Receipt)** để in lại. |
| **Đơn hàng bị treo khi thanh toán do mạng chập chờn** | Tín hiệu mạng đến máy chủ Odoo bị ngắt quãng. | Không tải lại trang (F5). POS của Odoo hoạt động ngoại tuyến (Offline mode). Đơn hàng sẽ tự động đồng bộ lên máy chủ ngay khi có mạng trở lại. |

