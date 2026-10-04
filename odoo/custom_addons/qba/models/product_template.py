from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    brand_id = fields.Many2one("qba.brand", string="Thương hiệu")
    brand_sku = fields.Char(string="SKU Thương hiệu")

    vehicle_ids = fields.Many2many(
        "qba.vehicle", "product_vehicle_rel", "product_id", "vehicle_id",
        string="Các loại xe áp dụng", tracking=True
    )

    engine_ids = fields.Many2many(
        "qba.engine", "product_engine_rel", "product_id", "engine_id",
        string="Động cơ áp dụng"
    )

    gearbox_ids = fields.Many2many(
        "qba.gearbox", "product_gearbox_rel", "product_id", "gearbox_id",
        string="Hộp số áp dụng"
    )

    barcode = fields.Char(string="Mã vạch", related="default_code", readonly=True)
    label_image = fields.Binary("Tem sản phẩm", attachment=True)

    # 1. Quản lý Đa Mã OE (OE Codes)
    oe_code_ids = fields.One2many(
        "qba.product.oe_code",
        "product_tmpl_id",
        string="Danh sách mã OE"
    )
    oe_codes_display = fields.Char(
        string="Mã OE",
        compute="_compute_oe_codes_display",
        store=True,
        index=True
    )

    # 2. Quản lý Ảnh Phụ (Extra Images)
    extra_image_ids = fields.One2many(
        "qba.product.image",
        "product_tmpl_id",
        string="Ảnh phụ sản phẩm"
    )
    extra_image_count = fields.Integer(
        string="Số lượng ảnh phụ",
        compute="_compute_extra_image_count"
    )

    # 3. Ngày nhập gần nhất & Ngày nhận báo giá gần nhất (Tính toán động từ lịch sử kho & đơn mua/báo giá)
    last_purchase_date = fields.Date(
        string="Ngày nhập gần nhất",
        compute="_compute_dates"
    )
    last_quotation_date = fields.Date(
        string="Ngày nhận báo giá gần nhất",
        compute="_compute_dates"
    )

    @api.depends("oe_code_ids.name")
    def _compute_oe_codes_display(self):
        for rec in self:
            codes = rec.oe_code_ids.mapped("name")
            rec.oe_codes_display = ", ".join(codes) if codes else ""

    @api.depends("extra_image_ids")
    def _compute_extra_image_count(self):
        for rec in self:
            rec.extra_image_count = len(rec.extra_image_ids)

    def _compute_dates(self):
        for rec in self:
            real_id = rec._origin.id or (isinstance(rec.id, int) and rec.id)
            if not real_id:
                continue

            # 1. Tính ngày nhập gần nhất từ dịch chuyển kho hoàn tất
            stock_move = self.env["stock.move"].search([
                ("product_id.product_tmpl_id", "=", real_id),
                ("state", "=", "done"),
                "|",
                ("picking_type_id.code", "=", "incoming"),
                "&", ("location_dest_id.usage", "=", "internal"), ("location_id.usage", "!=", "internal")
            ], order="date desc", limit=1)
            
            if not stock_move:
                stock_move = self.env["stock.move"].search([
                    ("product_id.product_tmpl_id", "=", real_id),
                    ("state", "=", "done"),
                    ("location_dest_id.usage", "=", "internal")
                ], order="date desc", limit=1)

            if stock_move and stock_move.date:
                rec.last_purchase_date = stock_move.date.date()
            elif not rec.last_purchase_date:
                # Fallback: Kiểm tra đơn mua hàng đã xác nhận
                po_line = self.env["purchase.order.line"].search([
                    ("product_id.product_tmpl_id", "=", real_id),
                    ("state", "in", ["purchase", "done"])
                ], order="id desc", limit=1)
                rec.last_purchase_date = po_line.order_id.date_order.date() if po_line and po_line.order_id and po_line.order_id.date_order else False

            # 2. Tính ngày nhận báo giá NCC gần nhất (Purchase RFQ/Quotation hoặc Báo giá bán)
            if not rec.last_quotation_date:
                po_rfq = self.env["purchase.order.line"].search([
                    ("product_id.product_tmpl_id", "=", real_id)
                ], order="id desc", limit=1)
                if po_rfq and po_rfq.order_id and po_rfq.order_id.date_order:
                    rec.last_quotation_date = po_rfq.order_id.date_order.date()
                else:
                    # Fallback 1: Kiểm tra báo giá bán hàng
                    so_line = self.env["sale.order.line"].search([
                        ("product_id.product_tmpl_id", "=", real_id)
                    ], order="id desc", limit=1)
                    if so_line and so_line.order_id and so_line.order_id.date_order:
                        rec.last_quotation_date = so_line.order_id.date_order.date()
                    elif rec.seller_ids:
                        # Fallback 2: Kiểm tra bảng giá nhà cung cấp
                        sellers = rec.seller_ids.sorted(key=lambda s: s.date_start or s.create_date or fields.Date.today(), reverse=True)
                        first_seller = sellers[0] if sellers else False
                        rec.last_quotation_date = first_seller.date_start or (first_seller.create_date.date() if first_seller and first_seller.create_date else False)

    def action_open_compare_wizard(self):
        """Mở bảng so sánh sản phẩm"""
        return {
            "name": "So Sánh Chi Tiết Sản Phẩm QBA",
            "type": "ir.actions.act_window",
            "res_model": "qba.product.compare.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_ids": [(6, 0, self.ids)],
            },
        }

    def open_label_wizard(self):
        self.ensure_one()
        return {
            'name': 'Tạo tem sản phẩm',
            'type': 'ir.actions.act_window',
            'res_model': 'qba.product.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
            },
        }

    def _compute_supplier_code(self):
        for rec in self:
            supplierinfo = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', rec.id),
                ('product_code', '!=', False)
            ], limit=1)
            rec.supplier_code = supplierinfo.product_code or ''

