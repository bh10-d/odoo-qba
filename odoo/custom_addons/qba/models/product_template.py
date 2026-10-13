from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .api_utils import get_odoo_api_headers


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
        string="Danh sách động cơ"
    )

    gearbox_ids = fields.Many2many(
        "qba.gearbox", "product_gearbox_rel", "product_id", "gearbox_id",
        string="Danh sách hộp số"
    )

    barcode = fields.Char(string="Mã vạch", related="default_code", readonly=True)
    label_image = fields.Binary("Tem sản phẩm", attachment=True)

    # 5. Liên kết Website SEO (Next.js / Express.js)
    website_product_url = fields.Char(
        string="Đường link Website",
        help="Đường link sản phẩm trên website SEO (vd: https://phutungotoquyba.com/products/loc-nhot-dong-co-123)"
    )
    website_product_id = fields.Integer(
        string="ID Sản phẩm Web",
        index=True,
        help="ID định danh sản phẩm trên database website"
    )
    website_product_slug = fields.Char(
        string="Slug Web"
    )
    is_website_linked = fields.Boolean(
        string="Đã liên kết Website",
        compute="_compute_is_website_linked",
        store=True,
        index=True
    )
    website_link_date = fields.Datetime(
        string="Ngày liên kết Web"
    )

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
    oe_codes_list = fields.Html(
        string="Danh sách mã OE (đa dòng)",
        compute="_compute_oe_codes_list",
        store=True
    )

    # 2. Thông số kỹ thuật & Bảo hành & Cầu & Mô tả nội bộ
    warranty = fields.Char(string="Bảo hành", default="Bảo hành 3 tháng")
    technical_specs = fields.Char(string="Ghi chú / Kích thước", help="Ví dụ: Dài 315, cao 15, ắc 25")
    axle_info = fields.Char(string="Cầu xe", help="Ví dụ: HOWO công nghệ MAN; Cầu láp 13T")
    internal_notes = fields.Text(string="Mô tả hàng hóa nội bộ")

    # Tương thích xe, động cơ, hộp số định dạng dấu ; cho Kanban
    vehicles_display = fields.Char(
        string="Xe áp dụng",
        compute="_compute_compatibility_display",
        store=True
    )
    engines_display = fields.Char(
        string="Động cơ áp dụng",
        compute="_compute_compatibility_display",
        store=True
    )
    gearboxes_display = fields.Char(
        string="Hộp số áp dụng",
        compute="_compute_compatibility_display",
        store=True
    )

    # 3. Quản lý Ảnh Phụ (Extra Images)
    extra_image_ids = fields.One2many(
        "qba.product.image",
        "product_tmpl_id",
        string="Ảnh phụ sản phẩm"
    )
    extra_image_count = fields.Integer(
        string="Số lượng ảnh phụ",
        compute="_compute_extra_image_count"
    )

    # 4. Ngày & Toa nhập gần nhất & Báo giá gần nhất
    last_purchase_date = fields.Date(
        string="Ngày nhập gần nhất",
        compute="_compute_dates"
    )
    last_purchase_code = fields.Char(
        string="Toa nhập gần nhất",
        compute="_compute_dates"
    )
    last_quotation_date = fields.Date(
        string="Ngày nhận báo giá gần nhất",
        compute="_compute_dates"
    )
    last_quotation_code = fields.Char(
        string="Toa báo giá gần nhất",
        compute="_compute_dates"
    )

    @api.depends("oe_code_ids.name")
    def _compute_oe_codes_display(self):
        for rec in self:
            codes = [oe.name.strip() for oe in rec.oe_code_ids if oe.name]
            rec.oe_codes_display = " | ".join(codes) if codes else ""

    @api.depends("oe_code_ids.name")
    def _compute_oe_codes_list(self):
        for rec in self:
            if not rec.oe_code_ids:
                rec.oe_codes_list = ""
                continue
            lines = [f'<div class="text-nowrap">{oe.name}</div>' for oe in rec.oe_code_ids]
            rec.oe_codes_list = "".join(lines)

    @api.depends("vehicle_ids.name", "vehicle_ids.complete_name", "engine_ids.name", "engine_ids.complete_name", "gearbox_ids.name", "gearbox_ids.complete_name")
    def _compute_compatibility_display(self):
        for rec in self:
            v_names = rec.vehicle_ids.mapped(lambda v: v.complete_name or v.name)
            e_names = rec.engine_ids.mapped(lambda e: e.complete_name or e.name)
            g_names = rec.gearbox_ids.mapped(lambda g: g.complete_name or g.name)
            rec.vehicles_display = "; ".join(v_names) if v_names else ""
            rec.engines_display = "; ".join(e_names) if e_names else ""
            rec.gearboxes_display = "; ".join(g_names) if g_names else ""

    @api.depends("extra_image_ids")
    def _compute_extra_image_count(self):
        for rec in self:
            real_id = rec._origin.id or (isinstance(rec.id, int) and rec.id)
            extra_cnt = len(rec.extra_image_ids)
            if not real_id:
                rec.extra_image_count = extra_cnt
                continue

            att_cnt = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'product.template'),
                ('res_id', '=', real_id),
                ('res_field', '=', False),
                ('mimetype', '=like', 'image/%')
            ])
            rec.extra_image_count = extra_cnt + att_cnt

    def _compute_dates(self):
        for rec in self:
            real_id = rec._origin.id or (isinstance(rec.id, int) and rec.id)
            rec.last_purchase_date = False
            rec.last_purchase_code = False
            rec.last_quotation_date = False
            rec.last_quotation_code = False
            if not real_id:
                continue

            uom_name = rec.uom_id.name or "bộ"

            # 1. Tính nhập gần nhất từ đơn mua hàng có số lượng > 0
            po_line = self.env["purchase.order.line"].search([
                ("product_id.product_tmpl_id", "=", real_id),
                ("product_qty", ">", 0)
            ], order="date_order desc, id desc", limit=1)

            if po_line and po_line.order_id:
                po = po_line.order_id
                code_name = po.name or "PO"
                dt = po.date_approve or po.date_order
                date_str = dt.strftime('%d/%m/%Y') if dt else ''
                rec.last_purchase_date = dt.date() if dt else False
                qty = po_line.qty_received if po_line.qty_received > 0 else po_line.product_qty
                rec.last_purchase_code = f"Nhập: {code_name} {date_str} ({qty:g} {uom_name})"
            else:
                # Fallback: Kiểm tra dịch chuyển kho hoàn tất
                stock_move = self.env["stock.move"].search([
                    ("product_id.product_tmpl_id", "=", real_id),
                    ("state", "=", "done"),
                    "|",
                    ("picking_type_id.code", "=", "incoming"),
                    "&", ("location_dest_id.usage", "=", "internal"), ("location_id.usage", "!=", "internal")
                ], order="date desc", limit=1)

                if stock_move and stock_move.date:
                    rec.last_purchase_date = stock_move.date.date()
                    date_str = stock_move.date.strftime('%d/%m/%Y')
                    qty = stock_move.quantity or stock_move.product_uom_qty
                    origin = stock_move.picking_id.origin or stock_move.origin or stock_move.picking_id.name or "VN"
                    rec.last_purchase_code = f"Nhập: {origin} {date_str} ({qty:g} {uom_name})"

            # 2. Tính ngày nhận báo giá gần nhất (Cứ ngày gần nhất là thể hiện báo giá)
            po_rfq = self.env["purchase.order.line"].search([
                ("product_id.product_tmpl_id", "=", real_id)
            ], order="date_order desc, id desc", limit=1)

            if po_rfq and po_rfq.order_id:
                dt = po_rfq.order_id.date_order
                date_str = dt.strftime('%d/%m/%Y') if dt else ''
                code_name = po_rfq.order_id.name or "PO"
                rec.last_quotation_date = dt.date() if dt else False
                rec.last_quotation_code = f"Báo giá: {code_name} {date_str}"
            else:
                # Fallback 1: Kiểm tra báo giá bán hàng
                so_line = self.env["sale.order.line"].search([
                    ("product_id.product_tmpl_id", "=", real_id)
                ], order="id desc", limit=1)
                if so_line and so_line.order_id and so_line.order_id.date_order:
                    rec.last_quotation_date = so_line.order_id.date_order.date()
                    date_str = so_line.order_id.date_order.strftime('%d/%m/%Y')
                    rec.last_quotation_code = f"Báo giá: {so_line.order_id.name or 'TV'} {date_str}"
                elif rec.seller_ids:
                    # Fallback 2: Kiểm tra bảng giá nhà cung cấp
                    def _get_seller_date(s):
                        if s.date_start:
                            return s.date_start
                        if s.create_date:
                            return s.create_date.date()
                        return fields.Date.today()

                    sellers = rec.seller_ids.sorted(key=_get_seller_date, reverse=True)
                    first_seller = sellers[0] if sellers else False
                    rec.last_quotation_date = first_seller.date_start or (first_seller.create_date.date() if first_seller and first_seller.create_date else False)
                    if rec.last_quotation_date:
                        date_str = rec.last_quotation_date.strftime('%d/%m/%Y')
                        vendor_name = first_seller.partner_id.name if first_seller.partner_id else "NCC"
                        rec.last_quotation_code = f"Báo giá: {vendor_name} {date_str}"

    @api.model
    def _parse_website_url_data(self, url):
        """Tách ID và slug từ URL website nếu người dùng nhập hoặc import trực tiếp"""
        if not url:
            return 0, False
        import re
        clean_url = str(url).strip().split("?")[0].split("#")[0].rstrip("/")
        p_id = 0
        match = re.search(r'(?:/|-)(\d+)$', clean_url)
        if match:
            try:
                p_id = int(match.group(1))
            except (ValueError, TypeError):
                pass
        parts = clean_url.split("/")
        p_slug = False
        if parts:
            last_segment = parts[-1]
            slug_match = re.match(r'^(.*?)(?:-\d+)?$', last_segment)
            if slug_match and slug_match.group(1):
                p_slug = slug_match.group(1)
        return p_id, p_slug

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('internal_notes'):
                notes = []
                if vals.get('description_sale'):
                    notes.append(vals['description_sale'].strip())
                if vals.get('description_purchase') and vals['description_purchase'].strip() not in notes:
                    notes.append(vals['description_purchase'].strip())
                if notes:
                    vals['internal_notes'] = "\n".join(notes)

            # Tự động trích xuất thông tin liên kết Web nếu có website_product_url
            if vals.get('website_product_url') and not vals.get('website_product_id'):
                p_id, p_slug = self._parse_website_url_data(vals['website_product_url'])
                if p_id:
                    vals['website_product_id'] = p_id
                if p_slug:
                    vals['website_product_slug'] = p_slug
                if not vals.get('website_link_date'):
                    vals['website_link_date'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        is_admin = self.env.is_admin() or self.env.user.has_group('base.group_system')
        if is_admin and 'is_storable' in vals:
            target_storable = vals.pop('is_storable')
            res = super().write(vals)
            self.env.cr.execute(
                "UPDATE product_template SET is_storable = %s WHERE id IN %s",
                (target_storable, tuple(self.ids))
            )
            self.invalidate_recordset(['is_storable'])
            variant_ids = self.with_context(active_test=False).mapped('product_variant_ids').ids
            if variant_ids:
                self.env.cr.execute(
                    "UPDATE product_product SET is_storable = %s WHERE id IN %s",
                    (target_storable, tuple(variant_ids))
                )
                self.env['product.product'].browse(variant_ids).invalidate_recordset(['is_storable'])
            return res

        # Tự động trích xuất hoặc dọn dẹp liên kết Web khi cập nhật website_product_url
        if 'website_product_url' in vals:
            url = vals.get('website_product_url')
            if url:
                if not vals.get('website_product_id'):
                    p_id, p_slug = self._parse_website_url_data(url)
                    if p_id:
                        vals['website_product_id'] = p_id
                    if p_slug:
                        vals['website_product_slug'] = p_slug
                if not vals.get('website_link_date'):
                    vals['website_link_date'] = fields.Datetime.now()
            else:
                vals.setdefault('website_product_id', False)
                vals.setdefault('website_product_slug', False)
                vals.setdefault('website_link_date', False)

        return super().write(vals)

    def _register_hook(self):
        """Tự động đồng bộ mô tả bán hàng / mua hàng sang mô tả hàng hóa nội bộ và chuẩn hóa mã OE dấu |"""
        super()._register_hook()
        try:
            # Chuẩn hóa dấu , thành | trong bảng product_template
            self.env.cr.execute("""
                UPDATE product_template 
                SET oe_codes_display = REPLACE(REPLACE(oe_codes_display, ', ', ' | '), ',', ' | ') 
                WHERE oe_codes_display LIKE '%,%';
            """)
            # Gom toàn bộ mô tả bán hàng / mua hàng về internal_notes nếu internal_notes đang trống
            products = self.search([
                ('internal_notes', '=', False),
                '|',
                ('description_sale', '!=', False),
                ('description_purchase', '!=', False)
            ])
            for p in products:
                notes = []
                if p.description_sale and p.description_sale.strip():
                    notes.append(p.description_sale.strip())
                if p.description_purchase and p.description_purchase.strip() and p.description_purchase.strip() not in notes:
                    notes.append(p.description_purchase.strip())
                if notes:
                    p.internal_notes = "\n".join(notes)
        except Exception:
            pass


    def action_view_extra_images(self):
        """Xem toàn bộ ảnh phụ của sản phẩm"""
        self.ensure_one()
        return {
            "name": f"Thư Viện Ảnh: {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "qba.product.image",
            "view_mode": "kanban,list,form",
            "views": [(False, "kanban"), (False, "list"), (False, "form")],
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {
                "default_product_tmpl_id": self.id,
                "default_name": f"Ảnh {self.name}",
            },
            "target": "current",
        }

    def action_open_multi_image_wizard(self):
        """Mở popup tải lên nhiều ảnh sản phẩm cùng lúc"""
        self.ensure_one()
        return {
            "name": f"Tải Lên Nhiều Ảnh: {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "qba.product.image.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
            },
        }

    def action_open_ai_assistant(self):
        """Mở Trợ lý AI tra cứu thông số / hướng dẫn đo"""
        self.ensure_one()
        context = {
            "default_user_query": f"Cách đo thông số kỹ thuật cho: {self.name}",
        }
        if "qba.ai.assistant" in self.env:
            return {
                "name": "Cách Lấy Thông Số Sản Phẩm (Trợ Lý AI)",
                "type": "ir.actions.act_window",
                "res_model": "qba.ai.assistant",
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "new",
                "context": context,
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Trợ Lý AI",
                "message": "Chức năng AI đang được xử lý hoặc module qba_ai chưa được bật.",
                "type": "info",
                "sticky": False,
            }
        }

    def action_open_compare_wizard(self):
        """Mở bảng so sánh sản phẩm"""
        return {
            "name": "So Sánh Chi Tiết Sản Phẩm QBA",
            "type": "ir.actions.act_window",
            "res_model": "qba.product.compare.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
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
            'views': [(False, 'form')],
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

    @api.depends("website_product_url", "website_product_id")
    def _compute_is_website_linked(self):
        for rec in self:
            rec.is_website_linked = bool(rec.website_product_url or rec.website_product_id)

    @api.onchange("website_product_url")
    def _onchange_website_product_url(self):
        if self.website_product_url:
            url = self.website_product_url.strip()
            clean_url = url.split("?")[0].split("#")[0].rstrip("/")
            import re
            # Lấy ID dạng /123 hoặc -123 ở cuối URL
            match = re.search(r'(?:/|-)(\d+)$', clean_url)
            if match:
                try:
                    self.website_product_id = int(match.group(1))
                except (ValueError, TypeError):
                    pass
            # Lấy slug
            parts = clean_url.split("/")
            if parts:
                last_segment = parts[-1]
                slug_match = re.match(r'^(.*?)(?:-\d+)?$', last_segment)
                if slug_match and slug_match.group(1):
                    self.website_product_slug = slug_match.group(1)
            if not self.website_link_date:
                self.website_link_date = fields.Datetime.now()
        else:
            self.website_product_id = False
            self.website_product_slug = False
            self.website_link_date = False

    def action_open_website_url(self):
        """Mở trực tiếp trang sản phẩm trên website hoặc mở popup liên kết nếu chưa có link"""
        self.ensure_one()
        url = self.website_product_url
        if not url and self.website_product_id:
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'qba.website_public_url', 'http://localhost:3000'
            ).rstrip('/')
            slug = self.website_product_slug or 'san-pham'
            url = f"{base_url}/products/{slug}-{self.website_product_id}"

        if not url:
            return self.action_open_web_link_wizard()

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_open_web_link_wizard(self):
        """Mở popup liên kết / tra cứu sản phẩm với Website SEO"""
        self.ensure_one()
        return {
            "name": f"Liên Kết Website SEO: {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "qba.product.web.link.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
                "default_target_url": self.website_product_url or "",
                "default_search_query": self.default_code or self.name or "",
            },
        }

    def action_unlink_website(self):
        """Hủy liên kết sản phẩm với Website cả ở Odoo lẫn Backend Express"""
        for rec in self:
            web_id = rec.website_product_id
            if web_id:
                success, auth_error = rec._notify_express_unlink(web_id)
                if auth_error:
                    raise UserError(_(
                        "Xác thực thất bại (401 Unauthorized)!\n\n"
                        "Khóa bí mật HMAC không chính xác hoặc không khớp với cấu hình Backend. Dữ liệu trên Odoo được giữ nguyên."
                    ))
            rec.website_product_url = False
            rec.website_product_id = False
            rec.website_product_slug = False
            rec.website_link_date = False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Đã hủy liên kết",
                "message": "Đã gỡ liên kết trên cả Odoo ERP và Website SEO thành công.",
                "type": "info",
                "sticky": False,
            }
        }

    def _notify_express_unlink(self, web_product_id):
        """Gửi lệnh hủy liên kết tới Backend Express để đặt odooProductId = null và isOdooLinked = false"""
        import requests
        api_param = self.env['ir.config_parameter'].sudo().get_param('qba.website_api_url') or 'http://host.docker.internal:5000/api/v1'
        candidates = [
            api_param.strip().rstrip('/'),
            'http://host.docker.internal:5000/api/v1',
            'http://172.18.0.1:5000/api/v1',
            'http://localhost:5000/api/v1',
        ]
        dedup = []
        for c in candidates:
            if c:
                if 'localhost:5000' in c or '127.0.0.1:5000' in c:
                    c = c.replace('localhost:5000', 'host.docker.internal:5000').replace('127.0.0.1:5000', 'host.docker.internal:5000')
                if c not in dedup:
                    dedup.append(c)

        headers = get_odoo_api_headers(self.env)
        success = False
        auth_error = False
        for ep in dedup:
            endpoint = f"{ep}/products/{web_product_id}/link-odoo"
            try:
                resp = requests.post(endpoint, json={'odooProductId': None}, headers=headers, timeout=2.5)
                if resp.status_code == 200:
                    success = True
                    break
                elif resp.status_code == 401:
                    auth_error = True
                    break
            except Exception:
                pass
        return success, auth_error

    def action_open_batch_sync_wizard(self):
        """Mở popup đối soát & đồng bộ liên kết Website theo SKU từ menu Hành động"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đồng bộ liên kết Website theo SKU',
            'res_model': 'qba.product.web.batch.sync.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'active_model': 'product.template',
                'active_ids': self.ids,
            }
        }

    def action_open_batch_unlink_wizard(self):
        """Mở popup xác nhận hủy liên kết Website hàng loạt từ menu Hành động"""
        valid_prods = self.exists().filtered(lambda p: p.is_website_linked)
        if not valid_prods:
            raise UserError(_("Không có sản phẩm nào trong các bản ghi được chọn đang có liên kết Website."))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Xác nhận hủy liên kết Website hàng loạt',
            'res_model': 'qba.product.web.batch.unlink.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'active_model': 'product.template',
                'active_ids': valid_prods.ids,
                'default_product_tmpl_ids': [(6, 0, valid_prods.ids)],
            }
        }



