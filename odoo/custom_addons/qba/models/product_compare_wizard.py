# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class QbaProductCompareWizard(models.TransientModel):
    _name = "qba.product.compare.wizard"
    _description = "Bảng So Sánh Nhanh 2-4 Sản Phẩm QBA"

    product_ids = fields.Many2many(
        "product.template",
        string="Sản phẩm được chọn",
        required=True
    )
    product_count = fields.Integer(string="Số lượng so sánh", compute="_compute_comparison_html")
    comparison_html = fields.Html(string="Bảng So Sánh Chi Tiết", compute="_compute_comparison_html", sanitize=False)

    @api.model
    def default_get(self, fields_list):
        res = super(QbaProductCompareWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids and self.env.context.get('active_model') == 'product.template':
            res['product_ids'] = [(6, 0, active_ids)]
        return res

    @api.onchange('product_ids')
    def _onchange_product_ids(self):
        if len(self.product_ids) > 4:
            self.product_ids = [(6, 0, self.product_ids.ids[:4])]
            return {
                'warning': {
                    'title': 'Giới hạn số lượng so sánh',
                    'message': 'Chỉ có thể chọn tối đa 4 sản phẩm cùng lúc để đảm bảo bảng đối chiếu hiển thị rõ ràng và chuẩn xác.',
                }
            }

    @api.constrains('product_ids')
    def _check_product_count(self):
        for rec in self:
            count = len(rec.product_ids)
            if count > 4:
                raise ValidationError(_("Chỉ hỗ trợ so sánh tối đa 4 sản phẩm cùng lúc để đảm bảo giao diện hiển thị rõ ràng."))

    def _get_product_image_src(self, product, high_res=False):
        """Lấy ảnh đại diện dạng base64 Data URI để hiển thị độc lập, không phụ thuộc URL host"""
        if high_res and product.image_1920:
            img_data = product.image_1920.decode('utf-8') if isinstance(product.image_1920, bytes) else product.image_1920
            return f"data:image/png;base64,{img_data}"
        if product.image_128:
            img_data = product.image_128.decode('utf-8') if isinstance(product.image_128, bytes) else product.image_128
            return f"data:image/png;base64,{img_data}"
        elif product.image_1920:
            img_data = product.image_1920.decode('utf-8') if isinstance(product.image_1920, bytes) else product.image_1920
            return f"data:image/png;base64,{img_data}"
        return "/web/static/img/placeholder.png"

    def _get_extra_image_src(self, extra_img, high_res=False):
        """Lấy ảnh phụ dạng base64 Data URI"""
        if high_res and extra_img.image_1920:
            img_data = extra_img.image_1920.decode('utf-8') if isinstance(extra_img.image_1920, bytes) else extra_img.image_1920
            return f"data:image/png;base64,{img_data}"
        if extra_img.image_128:
            img_data = extra_img.image_128.decode('utf-8') if isinstance(extra_img.image_128, bytes) else extra_img.image_128
            return f"data:image/png;base64,{img_data}"
        elif extra_img.image_1920:
            img_data = extra_img.image_1920.decode('utf-8') if isinstance(extra_img.image_1920, bytes) else extra_img.image_1920
            return f"data:image/png;base64,{img_data}"
        return "/web/static/img/placeholder.png"

    @api.depends('product_ids')
    def _compute_comparison_html(self):
        for rec in self:
            all_products = rec.product_ids
            # Giới hạn tối đa 4 sản phẩm
            is_over_limit = len(all_products) > 4
            selected_prods = all_products[:4] if is_over_limit else all_products
            rec.product_count = len(selected_prods)
            if not selected_prods:
                rec.comparison_html = """
                <div class="alert alert-info py-3 text-center">
                    <i class="fa fa-info-circle fa-2x mb-2 text-primary"></i>
                    <div class="fw-bold">Chưa có sản phẩm nào được chọn</div>
                    <div class="text-muted small mt-1">Vui lòng chọn hoặc tìm kiếm sản phẩm ở ô phía trên để xem chi tiết và đối chiếu.</div>
                </div>
                """
                continue

            # Sử dụng bản ghi gốc từ Database để luôn có đầy đủ ID thực tế và các trường ngày nhập, báo giá
            products = [p._origin if p._origin else p for p in selected_prods]
            show_placeholder_col = (len(products) == 1)

            # Cấu hình độ rộng cột
            if show_placeholder_col:
                col_spec_width = "22%"
                col_prod_width = "39%"
                col_slot_width = "39%"
            else:
                col_spec_width = "20%"
                col_prod_width = f"{int(80 / len(products))}%"
                col_slot_width = "0%"

            html = """<div class="qba-compare-wrapper table-responsive" style="overflow-x: auto;">"""

            if is_over_limit:
                html += f"""
                <div class="alert alert-warning py-2 px-3 mb-2 d-flex align-items-center rounded-3">
                    <i class="fa fa-exclamation-triangle me-2 text-warning"></i>
                    <div>
                        <b>Lưu ý:</b> Đã chọn {len(all_products)} sản phẩm. Hệ thống tự động hiển thị 4 sản phẩm đầu tiên để tối ưu bảng đối chiếu.
                    </div>
                </div>
                """

            if show_placeholder_col:
                p_first = products[0]
                sku_txt = f"[{p_first.default_code}] " if p_first.default_code else ""
                html += f"""
                <div class="alert alert-primary py-2 px-3 mb-2 d-flex align-items-center rounded-3">
                    <i class="fa fa-info-circle me-2 text-primary"></i>
                    <div>
                        <b>Đã tải đầy đủ thông số kỹ thuật:</b> {sku_txt}{p_first.name}.<br/>
                        <span class="small text-muted">Chọn thêm sản phẩm thứ 2, 3, 4 ở ô phía trên để đối chiếu song song.</span>
                    </div>
                </div>
                """

            html += f"""
                <table class="table table-bordered table-hover align-middle mb-0" style="table-layout: fixed; width: 100%;">
                    <colgroup>
                        <col style="width: {col_spec_width}; background-color: #f8f9fa;">
            """
            for _ in products:
                html += f'<col style="width: {col_prod_width};">'
            if show_placeholder_col:
                html += f'<col style="width: {col_slot_width}; background-color: #fafbfc;">'
            html += """
                    </colgroup>
                    <tbody>
            """

            # =================================================================
            # 1. Hàng Hình Ảnh & Slide Album Ảnh
            # =================================================================
            html += '<tr class="table-light"><th class="fw-bold text-muted">Hình Ảnh</th>'
            for p in products:
                # Thu thập toàn bộ danh sách ảnh của sản phẩm (ảnh chính + ảnh phụ)
                prod_images = []
                if p.image_1920 or p.image_128:
                    prod_images.append({
                        'src': self._get_product_image_src(p, high_res=False),
                        'zoom_src': self._get_product_image_src(p, high_res=True),
                        'title': p.name,
                        'alt': p.name,
                    })
                if p.extra_image_ids:
                    for extra in p.extra_image_ids:
                        prod_images.append({
                            'src': self._get_extra_image_src(extra, high_res=False),
                            'zoom_src': self._get_extra_image_src(extra, high_res=True),
                            'title': f"{p.name} - {extra.name or 'Ảnh phụ'}",
                            'alt': extra.name or "Ảnh phụ",
                        })

                if not prod_images:
                    prod_images.append({
                        'src': '/web/static/img/placeholder.png',
                        'zoom_src': '/web/static/img/placeholder.png',
                        'title': p.name,
                        'alt': p.name,
                    })

                total_imgs = len(prod_images)

                if total_imgs == 1:
                    img_item = prod_images[0]
                    content_html = f"""
                    <div class="qba-product-slider position-relative mx-auto" style="width: 100%; max-width: 260px;">
                        <div class="qba-slider-viewport position-relative d-flex align-items-center justify-content-center bg-white rounded border shadow-sm p-1" style="height: 200px; width: 100%; overflow: hidden;">
                            <img src="{img_item['src']}" data-zoom-src="{img_item['zoom_src']}" data-title="{img_item['title']}" class="qba-lightbox-trigger" style="max-height: 100%; max-width: 100%; width: auto; height: auto; object-fit: contain; cursor: zoom-in;" title="Bấm để phóng to hình ảnh" alt="{img_item['alt']}"/>
                        </div>
                    </div>
                    """
                else:
                    # Nhiều hình ảnh: Dạng Slide / Carousel với nút Next/Prev, số trang và thumbnail điều hướng
                    slides_html = ""
                    thumbs_html = ""
                    for idx, img_item in enumerate(prod_images):
                        active_style = "opacity: 1; z-index: 2; pointer-events: auto;" if idx == 0 else "opacity: 0; z-index: 1; pointer-events: none;"
                        slides_html += f"""
                        <div class="qba-slide position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center {'active' if idx == 0 else ''}" data-index="{idx}" style="{active_style} transition: opacity 0.25s ease-in-out; padding: 4px;">
                            <img src="{img_item['src']}" data-zoom-src="{img_item['zoom_src']}" data-title="{img_item['title']}" class="qba-lightbox-trigger" style="max-height: 100%; max-width: 100%; width: auto; height: auto; object-fit: contain; cursor: zoom-in;" title="Bấm để phóng to hình ảnh" alt="{img_item['alt']}"/>
                        </div>
                        """
                        active_thumb = " border-primary shadow-sm" if idx == 0 else ""
                        thumb_opacity = "opacity: 1;" if idx == 0 else "opacity: 0.6;"
                        thumb_border = "border: 2px solid #0d6efd !important;" if idx == 0 else "border: 1px solid #dee2e6 !important;"
                        thumbs_html += f"""
                        <div class="qba-slider-thumb rounded {'active' if idx == 0 else ''}{active_thumb}" data-index="{idx}" style="width: 38px; height: 38px; overflow: hidden; cursor: pointer; transition: all 0.15s ease; {thumb_opacity} {thumb_border}" title="Xem ảnh {idx + 1}">
                            <img src="{img_item['src']}" style="width: 100%; height: 100%; object-fit: cover; pointer-events: none;" alt="{img_item['alt']}"/>
                        </div>
                        """

                    content_html = f"""
                    <div class="qba-product-slider position-relative mx-auto" data-current-index="0" style="width: 100%; max-width: 260px;">
                        <div class="qba-slider-viewport position-relative d-flex align-items-center justify-content-center bg-white rounded border shadow-sm" style="height: 200px; width: 100%; overflow: hidden;">
                            {slides_html}

                            <!-- Nút chuyển Slide Trái / Phải -->
                            <button type="button" class="qba-slider-btn qba-slider-prev position-absolute start-0 top-50 translate-middle-y btn btn-light shadow-sm ms-1 rounded-circle d-flex align-items-center justify-content-center p-0" style="width: 28px; height: 28px; z-index: 5; opacity: 0.85; border: 1px solid rgba(0,0,0,0.15);" title="Ảnh trước">
                                <i class="fa fa-chevron-left" style="font-size: 11px;"></i>
                            </button>
                            <button type="button" class="qba-slider-btn qba-slider-next position-absolute end-0 top-50 translate-middle-y btn btn-light shadow-sm me-1 rounded-circle d-flex align-items-center justify-content-center p-0" style="width: 28px; height: 28px; z-index: 5; opacity: 0.85; border: 1px solid rgba(0,0,0,0.15);" title="Ảnh kế tiếp">
                                <i class="fa fa-chevron-right" style="font-size: 11px;"></i>
                            </button>

                            <!-- Chỉ số ảnh (Badge counter) -->
                            <span class="qba-slider-counter badge position-absolute bottom-0 end-0 m-2 px-2 py-1" style="background: rgba(0,0,0,0.65); color: #fff; font-size: 10px; font-weight: 500; border-radius: 10px; z-index: 5;">
                                1 / {total_imgs}
                            </span>
                        </div>

                        <!-- Hàng ảnh thumbnail bên dưới -->
                        <div class="qba-slider-thumbs d-flex justify-content-center align-items-center flex-wrap gap-1 mt-2">
                            {thumbs_html}
                        </div>
                    </div>
                    """

                html += f"""
                <td class="text-center p-2 align-top">
                    {content_html}
                </td>
                """
            if show_placeholder_col:
                html += """
                <td class="text-center p-3" style="background-color: #fcfdfe; border: 2px dashed #b6d4fe;">
                    <div class="py-4">
                        <div class="fw-bold text-dark">Thêm sản phẩm thứ 2</div>
                        <div class="small text-muted mt-1">Chọn ở thanh tìm kiếm phía trên</div>
                    </div>
                </td>
                """
            html += '</tr>'

            # =================================================================
            # 2. Mã SKU & Tên Sản Phẩm
            # =================================================================
            html += '<tr><th class="fw-bold">Mã SKU &amp; Tên</th>'
            for p in products:
                sku_badge = f'<span class="badge bg-primary text-white mb-1" style="font-size: 0.85rem;">{p.default_code}</span>' if p.default_code else '<span class="text-muted fst-italic">Chưa có SKU</span>'
                html += f"""
                <td class="p-3">
                    <div>{sku_badge}</div>
                    <div class="fw-bold text-dark mt-1" style="font-size: 0.95rem; line-height: 1.35;">{p.name}</div>
                </td>
                """
            if show_placeholder_col:
                html += '<td class="p-3 text-muted fst-italic text-center" style="background-color: #fafbfc;">(Đang chờ chọn sản phẩm đối chiếu)</td>'
            html += '</tr>'

            # =================================================================
            # 3. Giá Bán Niêm Yết
            # =================================================================
            html += '<tr><th class="fw-bold">Giá Bán Niêm Yết</th>'
            for p in products:
                price_str = f"{p.list_price:,.0f} {p.currency_id.symbol or 'VNĐ'}"
                html += f"""
                <td class="p-3">
                    <span class="fs-5 fw-bold text-danger">{price_str}</span>
                </td>
                """
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # =================================================================
            # 4. Số Lượng Tồn Kho
            # =================================================================
            html += '<tr><th class="fw-bold">Số Lượng Tồn Kho</th>'
            for p in products:
                qty = p.qty_available
                qty_class = "success" if qty > 0 else "danger"
                qty_label = f"{qty:g} {p.uom_id.name or ''}" if qty > 0 else f"Hết hàng (0 {p.uom_id.name or ''})"
                html += f"""
                <td class="p-3">
                    <span class="badge bg-{qty_class} fs-6 px-2 py-1">{qty_label}</span>
                </td>
                """
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # =================================================================
            # 5. Mã OE (OE Code - Đa mã chính hãng)
            # =================================================================
            html += '<tr><th class="fw-bold">Mã Phụ Tùng OE</th>'
            for p in products:
                oe_tags = ""
                if p.oe_code_ids:
                    for oe in p.oe_code_ids:
                        brand_note = f" ({oe.brand_id.name})" if oe.brand_id else ""
                        oe_tags += f'<span class="badge bg-light text-dark border me-1 mb-1" style="font-family: monospace; font-size: 0.82rem;">{oe.name}{brand_note}</span>'
                else:
                    oe_tags = '<span class="text-muted fst-italic">Không có mã OE</span>'
                html += f'<td class="p-3">{oe_tags}</td>'
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # =================================================================
            # 6. Thương Hiệu & Bảo Hành & Kích Thước
            # =================================================================
            html += '<tr><th class="fw-bold">Thương Hiệu &amp; Bảo Hành</th>'
            for p in products:
                brand_name = p.brand_id.name if p.brand_id else '<span class="text-muted fst-italic">Chưa xác định</span>'
                warranty_val = p.warranty or '<span class="text-muted fst-italic">N/A</span>'
                html += f"""
                <td class="p-3">
                    <div class="fw-semibold text-dark">{brand_name}</div>
                    <div class="mt-1"><span class="badge bg-light text-primary border">{warranty_val}</span></div>
                </td>
                """
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # Kích thước & Thông số đo
            html += '<tr><th class="fw-bold">Ghi Chú / Kích Thước</th>'
            for p in products:
                specs = p.technical_specs or '<span class="text-muted fst-italic">Chưa cập nhật thông số</span>'
                html += f'<td class="p-3 fw-semibold text-secondary">{specs}</td>'
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # =================================================================
            # 7. Toa Nhập Hàng Gần Nhất (kèm số lượng)
            # =================================================================
            html += '<tr><th class="fw-bold">Toa Nhập Gần Nhất</th>'
            for p in products:
                last_purchase = p.last_purchase_code or (f"VN {p.last_purchase_date.strftime('%d/%m/%Y')}" if p.last_purchase_date else False)
                if last_purchase:
                    val_html = f'<span class="fw-semibold text-dark">{last_purchase}</span>'
                else:
                    val_html = '<span class="text-muted fst-italic">Chưa có lịch sử nhập</span>'
                html += f'<td class="p-3">{val_html}</td>'
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # =================================================================
            # 8. Toa Báo Giá Gần Nhất
            # =================================================================
            html += '<tr><th class="fw-bold">Toa Báo Giá Gần Nhất</th>'
            for p in products:
                last_quote = p.last_quotation_code or (f"TV {p.last_quotation_date.strftime('%d/%m/%Y')}" if p.last_quotation_date else False)
                if last_quote:
                    val_html = f'<span class="fw-semibold text-dark">{last_quote}</span>'
                else:
                    val_html = '<span class="text-muted fst-italic">Chưa có báo giá</span>'
                html += f'<td class="p-3">{val_html}</td>'
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # =================================================================
            # 9. Tương Thích Xe, Động Cơ, Hộp Số & Cầu
            # =================================================================
            html += '<tr><th class="fw-bold">Động Cơ, Hộp Số &amp; Cầu</th>'
            for p in products:
                engines = "; ".join(p.engine_ids.mapped('name')) if p.engine_ids else "N/A"
                gearboxes = "; ".join(p.gearbox_ids.mapped('name')) if p.gearbox_ids else "N/A"
                axle = p.axle_info or "N/A"
                html += f"""
                <td class="p-3 small">
                    <div><b>Động cơ:</b> {engines}</div>
                    <div><b>Hộp số:</b> {gearboxes}</div>
                    <div><b>Cầu:</b> {axle}</div>
                </td>
                """
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # =================================================================
            # 10. Dòng Xe Áp Dụng
            # =================================================================
            html += '<tr><th class="fw-bold">Dòng Xe Áp Dụng</th>'
            for p in products:
                vehicles = "; ".join(p.vehicle_ids.mapped('name')) if p.vehicle_ids else '<span class="text-muted fst-italic">Nhiều dòng xe</span>'
                html += f'<td class="p-3 small">{vehicles}</td>'
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            # =================================================================
            # 11. Ghi Chú Bán Hàng (Note)
            # =================================================================
            html += '<tr><th class="fw-bold">Ghi Chú Bán Hàng</th>'
            for p in products:
                desc = p.description_sale or '<span class="text-muted fst-italic">Không có ghi chú</span>'
                html += f'<td class="p-3 small text-muted">{desc}</td>'
            if show_placeholder_col:
                html += '<td class="p-3 text-muted text-center" style="background-color: #fafbfc;">---</td>'
            html += '</tr>'

            html += """
                    </tbody>
                </table>
            </div>
            """
            rec.comparison_html = html
