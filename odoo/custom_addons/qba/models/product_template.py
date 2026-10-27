import math
from datetime import datetime, date, time
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .api_utils import get_odoo_api_headers


def _to_datetime(val):
    if not val:
        return False
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, time.min)
    return False


def _chunk_and_balance(names, target_chunk=5):
    """Chia đều danh sách mã/tên xe/động cơ/hộp số thành các dòng cân đối, mỗi dòng tầm 5 mã"""
    if not names:
        return ""
    n = len(names)
    num_lines = math.ceil(n / target_chunk)
    if num_lines <= 1:
        return " | ".join(names)
    per_line = math.ceil(n / num_lines)
    lines = []
    for i in range(0, n, per_line):
        chunk = names[i:i + per_line]
        lines.append(" | ".join(chunk))
    return "\n".join(lines)


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

    axle_ids = fields.Many2many(
        "qba.axle", "product_axle_rel", "product_id", "axle_id",
        string="Cầu xe áp dụng"
    )

    barcode = fields.Char(string="Mã vạch", related="default_code", readonly=True)
    label_image = fields.Binary("Tem sản phẩm", attachment=True)
    supplier_code = fields.Char(
        string="Mã nhà cung cấp",
        compute="_compute_supplier_code",
        store=True,
    )

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

    # Cờ quyền Quản Trị Viên (System Admin)
    is_system_admin = fields.Boolean(
        string="Là Quản Trị Viên",
        compute="_compute_is_system_admin"
    )

    # 2. Thông số kỹ thuật & Bảo hành & Cầu & Mô tả SP
    warranty_days = fields.Integer(string="Bảo hành (ngày)", default=90)
    warranty = fields.Char(string="Bảo hành", compute="_compute_warranty", store=True, readonly=False)
    technical_specs = fields.Text(string="Mô tả SP", help="Kích thước, thông số kỹ thuật, mô tả chi tiết sản phẩm")
    axle_info = fields.Char(string="Cầu xe", help="Ví dụ: HOWO công nghệ MAN; Cầu láp 13T")
    internal_notes = fields.Text(string="Mô tả hàng hóa nội bộ")
    attachment_images_preview = fields.Html(
        string="Hình ảnh đính kèm",
        compute="_compute_attachment_images_preview",
        sanitize=False
    )

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
    axles_display = fields.Char(
        string="Cầu xe áp dụng",
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
            codes = [oe.name.strip() for oe in rec.oe_code_ids if oe.name and oe.name.strip()]
            rec.oe_codes_display = _chunk_and_balance(codes, 5)

    @api.depends("oe_code_ids.name")
    def _compute_oe_codes_list(self):
        for rec in self:
            if not rec.oe_code_ids:
                rec.oe_codes_list = ""
                continue
            lines = [f'<div class="text-nowrap">{oe.name}</div>' for oe in rec.oe_code_ids]
            rec.oe_codes_list = "".join(lines)

    @api.depends(
        "vehicle_ids.name", "vehicle_ids.complete_name",
        "engine_ids.name", "engine_ids.complete_name",
        "gearbox_ids.name", "gearbox_ids.complete_name",
        "axle_ids.name", "axle_ids.complete_name",
        "axle_info"
    )
    def _compute_compatibility_display(self):
        for rec in self:
            v_names = [v.strip() for v in rec.vehicle_ids.mapped(lambda v: v.complete_name or v.name or "") if v.strip()]
            e_names = [e.strip() for e in rec.engine_ids.mapped(lambda e: e.complete_name or e.name or "") if e.strip()]
            g_names = [g.strip() for g in rec.gearbox_ids.mapped(lambda g: g.complete_name or g.name or "") if g.strip()]
            a_names = [a.strip() for a in rec.axle_ids.mapped(lambda a: a.complete_name or a.name or "") if a.strip()]
            rec.vehicles_display = _chunk_and_balance(v_names, 5)
            rec.engines_display = _chunk_and_balance(e_names, 5)
            rec.gearboxes_display = _chunk_and_balance(g_names, 5)
            if a_names:
                rec.axles_display = _chunk_and_balance(a_names, 5)
            elif rec.axle_info:
                rec.axles_display = rec.axle_info.strip()
            else:
                rec.axles_display = False

    def _compute_is_system_admin(self):
        is_admin = self.env.is_admin() or self.env.user.has_group('base.group_system')
        for rec in self:
            rec.is_system_admin = is_admin

    @api.depends("warranty_days")
    def _compute_warranty(self):
        for rec in self:
            if rec.warranty_days > 0:
                rec.warranty = f"Bảo hành {rec.warranty_days} ngày"
            elif rec.warranty_days == 0:
                rec.warranty = "Không bảo hành"
            else:
                rec.warranty = False

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

    def _compute_attachment_images_preview(self):
        for rec in self:
            real_id = rec._origin.id or (isinstance(rec.id, int) and rec.id)
            if not real_id:
                rec.attachment_images_preview = False
                continue

            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'product.template'),
                ('res_id', '=', real_id),
                ('res_field', '=', False),
                ('mimetype', '=like', 'image/%')
            ], order="id desc")

            extra_imgs = rec.extra_image_ids

            if not attachments and not extra_imgs:
                rec.attachment_images_preview = """
                    <div class="qba-attachment-empty text-muted small py-2 text-center" style="font-size: 11px;">
                        <i class="fa fa-paperclip me-1"/>Chưa có ảnh phụ.<br/>Bấm nút <b>Tập tin</b> ở thanh bên phải (Chatter) để đính kèm ảnh.
                    </div>
                """
                continue

            html_parts = ['<div class="qba-attachment-gallery d-flex flex-wrap gap-2 pt-1 pb-1 justify-content-center">']
            for att in attachments:
                name = (att.name or "Ảnh đính kèm").replace('"', '&quot;')
                desc = (att.description or name).replace('"', '&quot;')
                html_parts.append(f'''
                    <div class="qba-thumb-box position-relative text-center border rounded p-1 bg-white shadow-sm" style="width: 66px;">
                        <div class="qba-thumb-wrapper position-relative" style="width: 58px; height: 58px; overflow: visible;">
                            <img src="/web/image/{att.id}" alt="{name}" title="{desc} (Rê chuột để phóng to x4 - Bấm để mở xem lớn)" class="qba-img-hover-scale-4x qba-lightbox-trigger rounded w-100 h-100 object-fit-contain" style="cursor: pointer; background: #fafafa;"/>
                        </div>
                        <div class="qba-thumb-title text-truncate small fw-medium mt-1 text-dark" style="font-size: 10px; max-width: 58px;" title="{name}">
                            {name}
                        </div>
                    </div>
                ''')

            for extra in extra_imgs:
                name = (extra.name or "Ảnh chi tiết").replace('"', '&quot;')
                html_parts.append(f'''
                    <div class="qba-thumb-box position-relative text-center border rounded p-1 bg-white shadow-sm" style="width: 66px;">
                        <div class="qba-thumb-wrapper position-relative" style="width: 58px; height: 58px; overflow: visible;">
                            <img src="/web/image/qba.product.image/{extra.id}/image_1920" alt="{name}" title="{name} (Rê chuột để phóng to x4 - Bấm để mở xem lớn)" class="qba-img-hover-scale-4x qba-lightbox-trigger rounded w-100 h-100 object-fit-contain" style="cursor: pointer; background: #fafafa;"/>
                        </div>
                        <div class="qba-thumb-title text-truncate small fw-medium mt-1 text-dark" style="font-size: 10px; max-width: 58px;" title="{name}">
                            {name}
                        </div>
                    </div>
                ''')

            html_parts.append('</div>')
            rec.attachment_images_preview = "".join(html_parts)

    def _compute_dates(self):
        for rec in self:
            real_id = rec._origin.id or (isinstance(rec.id, int) and rec.id)
            rec.last_purchase_date = False
            rec.last_purchase_code = False
            rec.last_quotation_date = False
            rec.last_quotation_code = False
            dt_purchase = False
            dt_quote = False
            if not real_id:
                continue

            uom_str = rec.uom_id.name.lower() if rec.uom_id.name else "cái"

            # 1. Tính nhập gần nhất từ đơn mua hàng có số lượng > 0
            po_line = self.env["purchase.order.line"].search([
                ("product_id.product_tmpl_id", "=", real_id),
                ("product_qty", ">", 0),
                ("order_id.state", "in", ["purchase", "done"]),
            ], order="date_order desc, id desc", limit=1)

            if not po_line:
                po_line = self.env["purchase.order.line"].search([
                    ("product_id.product_tmpl_id", "=", real_id),
                    ("product_qty", ">", 0),
                ], order="date_order desc, id desc", limit=1)

            if po_line and po_line.order_id:
                po = po_line.order_id
                code_name = po.name or "PO"
                partner_ref = po.partner_ref.strip() if po.partner_ref else ""
                dt_purchase = po.date_approve or po.date_order
                date_str = dt_purchase.strftime('%d/%m/%y') if dt_purchase else ''
                rec.last_purchase_date = dt_purchase.date() if dt_purchase else False
                qty = po_line.product_qty

                # Định dạng chuẩn theo mockup: P01998 (BA 27/06/26) 1 cái
                if partner_ref:
                    po_display = f"{code_name} ({partner_ref})"
                else:
                    partner_name = po.partner_id.name or ""
                    short_partner = partner_name.split(" - ")[0].strip() if " - " in partner_name else partner_name[:5].strip()
                    if short_partner and date_str:
                        po_display = f"{code_name} ({short_partner} {date_str})"
                    elif date_str:
                        po_display = f"{code_name} {date_str}".strip()
                    else:
                        po_display = code_name

                rec.last_purchase_code = f"Nhập: {po_display} {qty:g} {uom_str}"
            else:
                # Fallback: Kiểm tra dịch chuyển kho hoàn tất
                stock_move = self.env["stock.move"].search([
                    ("product_id.product_tmpl_id", "=", real_id),
                    ("state", "=", "done"),
                    "|",
                    ("picking_type_id.code", "=", "incoming"),
                    "&", ("location_dest_id.usage", "=", "internal"), ("location_id.usage", "!=", "internal")
                ], order="date desc, id desc", limit=1)

                if stock_move and stock_move.date:
                    dt_purchase = stock_move.date
                    rec.last_purchase_date = stock_move.date.date()
                    date_str = stock_move.date.strftime('%d/%m/%y')
                    qty = stock_move.quantity or stock_move.product_uom_qty
                    origin = stock_move.picking_id.origin or stock_move.origin or stock_move.picking_id.name or "Kho"
                    rec.last_purchase_code = f"Nhập: {origin} {date_str} {qty:g} {uom_str}"

            # 2. Tính đơn báo giá gần nhất:
            # Chỉ lấy từ đơn Purchase Order có SL = 0 (quy trình lưu báo giá NCC) hoặc RFQ (draft, sent)
            po_quote = self.env["purchase.order.line"].search([
                ("product_id.product_tmpl_id", "=", real_id),
                "|",
                ("product_qty", "=", 0),
                ("order_id.state", "in", ["draft", "sent"]),
            ], order="date_order desc, id desc", limit=1)

            po_quote_code = False
            po_quote_date = False
            dt_po_quote = False

            if po_quote and po_quote.order_id:
                po_q = po_quote.order_id
                dt_po_quote = po_q.date_approve or po_q.date_order
                po_quote_date = dt_po_quote.date() if dt_po_quote else False
                date_str = dt_po_quote.strftime('%d/%m/%y') if dt_po_quote else ''
                q_name = po_q.name or "PO"
                q_pref = po_q.partner_ref.strip() if po_q.partner_ref else ""

                # Định dạng chuẩn theo mockup: P01999 (VN 09/10/26)
                if q_pref:
                    q_display = f"{q_name} ({q_pref})"
                else:
                    partner_name = po_q.partner_id.name or ""
                    short_partner = partner_name.split(" - ")[0].strip() if " - " in partner_name else partner_name[:5].strip()
                    if short_partner and date_str:
                        q_display = f"{q_name} ({short_partner} {date_str})"
                    elif date_str:
                        q_display = f"{q_name} {date_str}".strip()
                    else:
                        q_display = q_name

                po_quote_code = f"Báo giá: {q_display}"

            # 3. Quy tắc thể hiện ngày báo giá tại trang tổng theo đúng chữ đỏ và mũi tên trong ảnh:
            # - Báo giá CHỈ lấy từ đơn PO báo giá (product_qty == 0 hoặc RFQ) với định dạng P.... (Mã NCC).
            # - Nếu không có đơn PO báo giá: Không hiển thị dòng báo giá ngoài trang tổng.
            # - "Nếu ngày xác nhận của nhập hàng (SL>0) gần hơn xác nhận của báo giá (=0) => ko cần thể hiện ngày báo giá tại trang tổng":
            #   Ẩn dòng báo giá khi ngày xác nhận của lần nhập hàng mới hơn hoặc bằng lần báo giá.
            # - Chỉ thể hiện khi có đơn PO báo giá và báo giá MỚI HƠN lần nhập hàng (như BNM.017) hoặc sản phẩm chưa từng nhập hàng.
            if po_quote_code:
                if dt_purchase and dt_po_quote:
                    dt_p_cmp = _to_datetime(dt_purchase)
                    dt_q_cmp = _to_datetime(dt_po_quote)
                    if dt_p_cmp and dt_q_cmp and dt_p_cmp >= dt_q_cmp:
                        rec.last_quotation_code = False
                        rec.last_quotation_date = False
                    else:
                        rec.last_quotation_code = po_quote_code
                        rec.last_quotation_date = po_quote_date
                else:
                    rec.last_quotation_code = po_quote_code
                    rec.last_quotation_date = po_quote_date
            else:
                rec.last_quotation_code = False
                rec.last_quotation_date = False

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
            if not vals.get('technical_specs'):
                notes = []
                if vals.get('internal_notes'):
                    notes.append(vals['internal_notes'].strip())
                if vals.get('description_sale') and vals['description_sale'].strip() not in notes:
                    notes.append(vals['description_sale'].strip())
                if vals.get('description_purchase') and vals['description_purchase'].strip() not in notes:
                    notes.append(vals['description_purchase'].strip())
                if notes:
                    vals['technical_specs'] = "\n".join(notes)
            if not vals.get('internal_notes') and vals.get('technical_specs'):
                vals['internal_notes'] = vals['technical_specs']

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
        """Tự động đồng bộ mô tả sang Mô tả SP, chuẩn hóa bảo hành, mã OE và migrate ảnh phụ sang ir.attachment"""
        super()._register_hook()
        try:
            # Chuẩn hóa dấu , thành | trong bảng product_template
            self.env.cr.execute("""
                UPDATE product_template 
                SET oe_codes_display = REPLACE(REPLACE(oe_codes_display, ', ', ' | '), ',', ' | ') 
                WHERE oe_codes_display LIKE '%,%';
            """)

            # Gộp dữ liệu internal_notes vào technical_specs nếu technical_specs chưa có hoặc chưa chứa internal_notes
            self.env.cr.execute("""
                UPDATE product_template
                SET technical_specs = CASE
                    WHEN (technical_specs IS NULL OR technical_specs = '') AND (internal_notes IS NOT NULL AND internal_notes != '') THEN internal_notes
                    WHEN (technical_specs IS NOT NULL AND technical_specs != '') AND (internal_notes IS NOT NULL AND internal_notes != '') AND position(internal_notes in technical_specs) = 0 THEN technical_specs || E'\n' || internal_notes
                    ELSE technical_specs
                END
                WHERE internal_notes IS NOT NULL AND internal_notes != '';
            """)

            # Chuẩn hóa số ngày bảo hành warranty_days từ warranty cũ nếu warranty_days chưa có giá trị
            self.env.cr.execute("""
                UPDATE product_template
                SET warranty_days = CASE
                    WHEN warranty ILIKE '%30 ngày%' OR warranty ILIKE '%1 tháng%' THEN 30
                    WHEN warranty ILIKE '%60 ngày%' OR warranty ILIKE '%2 tháng%' THEN 60
                    WHEN warranty ILIKE '%3 tháng%' OR warranty ILIKE '%90 ngày%' THEN 90
                    WHEN warranty ILIKE '%6 tháng%' OR warranty ILIKE '%180 ngày%' THEN 180
                    WHEN warranty ILIKE '%1 năm%' OR warranty ILIKE '%12 tháng%' OR warranty ILIKE '%365 ngày%' THEN 365
                    WHEN warranty ILIKE '%không%' THEN 0
                    ELSE 90
                END
                WHERE warranty_days IS NULL OR warranty_days = 0;

                UPDATE product_template
                SET warranty = CASE
                    WHEN warranty_days > 0 THEN 'Bảo hành ' || warranty_days || ' ngày'
                    WHEN warranty_days = 0 THEN 'Không bảo hành'
                    ELSE 'Bảo hành 90 ngày'
                END;
            """)

            # Đồng bộ ảnh từ qba.product.image sang ir.attachment (đảm bảo không mất ảnh cũ)
            extra_imgs = self.env['qba.product.image'].search([])
            for img in extra_imgs:
                if img.image_1920 and img.product_tmpl_id:
                    existing = self.env['ir.attachment'].search([
                        ('res_model', '=', 'product.template'),
                        ('res_id', '=', img.product_tmpl_id.id),
                        ('name', '=', img.name or 'Ảnh chi tiết')
                    ], limit=1)
                    if not existing:
                        self.env['ir.attachment'].create({
                            'name': img.name or f"Ảnh {img.product_tmpl_id.name}",
                            'res_model': 'product.template',
                            'res_id': img.product_tmpl_id.id,
                            'datas': img.image_1920,
                            'mimetype': 'image/jpeg',
                            'description': img.name or '',
                        })
        except Exception:
            pass

    def action_view_extra_images(self):
        """Xem toàn bộ tập tin & ảnh đính kèm của sản phẩm"""
        self.ensure_one()
        return {
            "name": f"Tập tin / Ảnh: {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "kanban,list,form",
            "views": [(False, "kanban"), (False, "list"), (False, "form")],
            "domain": [
                ("res_model", "=", "product.template"),
                ("res_id", "=", self.id),
            ],
            "context": {
                "default_res_model": "product.template",
                "default_res_id": self.id,
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
        first_seller = self.seller_ids.filtered(lambda s: s.product_code)[:1]
        uom_str = f"1 {self.uom_id.name}".strip() if self.uom_id else "1 Cái"
        return {
            'name': 'Tạo tem sản phẩm',
            'type': 'ir.actions.act_window',
            'res_model': 'qba.product.label.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_custom_name': self.name,
                'default_supplier_product_code': first_seller.id if first_seller else False,
                'default_supplier_code': first_seller.product_code if first_seller else '',
                'default_nhap_date': self.last_purchase_date or fields.Date.context_today(self),
                'default_dinh_luong': uom_str,
            },
        }

    @api.depends("seller_ids.product_code")
    def _compute_supplier_code(self):
        for rec in self:
            first_seller = rec.seller_ids.filtered(lambda s: s.product_code)[:1]
            rec.supplier_code = first_seller.product_code or ''

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



