import math
from datetime import datetime, date, time
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
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
    website_show_price = fields.Boolean(
        string="Hiển thị giá trên Web",
        default=True,
        help="Bật để hiển thị giá bán niêm yết trên Website SEO. Tắt nếu muốn ẩn giá và hiển thị 'Liên hệ Báo giá'."
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
        compute="_compute_is_system_admin",
        default=lambda self: self.env.is_admin() or self.env.user.has_group('base.group_system'),
    )

    # 2. Thông số kỹ thuật & Bảo hành & Cầu & Mô tả SP
    warranty_days = fields.Integer(string="Bảo hành (ngày)", default=0)
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

    @api.depends_context('uid')
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
        real_ids = [rec._origin.id or (isinstance(rec.id, int) and rec.id) for rec in self]
        valid_ids = [i for i in real_ids if i]
        att_counts = {}
        if valid_ids:
            self.env.cr.execute("""
                SELECT res_id, count(id)
                FROM ir_attachment
                WHERE res_model = 'product.template'
                  AND res_id IN %s
                  AND res_field IS NULL
                  AND mimetype LIKE 'image/%%'
                GROUP BY res_id
            """, [tuple(valid_ids)])
            att_counts = dict(self.env.cr.fetchall())

        for rec in self:
            real_id = rec._origin.id or (isinstance(rec.id, int) and rec.id)
            extra_cnt = len(rec.extra_image_ids)
            rec.extra_image_count = extra_cnt + att_counts.get(real_id, 0)

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
                    <div class="qba-attachment-empty text-muted small py-1 text-center" style="font-size: 11px;">
                        <i class="fa fa-info-circle me-1"/>Chưa có ảnh chi tiết
                    </div>
                """
                continue

            html_parts = ['<div class="qba-attachment-gallery d-flex flex-wrap gap-1 pt-1 pb-1 justify-content-start">']
            for att in attachments:
                name = (att.name or "Ảnh đính kèm").replace('"', '&quot;')
                desc = (att.description or name).replace('"', '&quot;')
                html_parts.append(f'''
                    <div class="qba-thumb-box position-relative text-center border rounded p-1 bg-white shadow-sm" style="width: 46px; height: 46px;" title="{desc} (Click xem ảnh lớn)">
                        <div class="qba-thumb-wrapper position-relative w-100 h-100 overflow-hidden">
                            <img src="/web/image/{att.id}" alt="{name}" class="qba-img-hover-scale-4x qba-lightbox-trigger rounded w-100 h-100 object-fit-cover" style="cursor: pointer;"/>
                        </div>
                    </div>
                ''')

            for extra in extra_imgs:
                name = (extra.name or "Ảnh chi tiết").replace('"', '&quot;')
                html_parts.append(f'''
                    <div class="qba-thumb-box position-relative text-center border rounded p-1 bg-white shadow-sm" style="width: 46px; height: 46px;" title="{name} (Click xem ảnh lớn)">
                        <div class="qba-thumb-wrapper position-relative w-100 h-100 overflow-hidden">
                            <img src="/web/image/qba.product.image/{extra.id}/image_1920" alt="{name}" class="qba-img-hover-scale-4x qba-lightbox-trigger rounded w-100 h-100 object-fit-cover" style="cursor: pointer;"/>
                        </div>
                    </div>
                ''')

            html_parts.append('</div>')
            rec.attachment_images_preview = "".join(html_parts)

    def _compute_dates(self):
        real_ids = [rec._origin.id or (isinstance(rec.id, int) and rec.id) for rec in self]
        valid_ids = [i for i in real_ids if i]

        po_done_map = {}
        po_any_map = {}
        moves_map = {}
        quotes_map = {}

        if valid_ids:
            # 1. Batch PO done / purchase (qty > 0)
            self.env.cr.execute("""
                SELECT DISTINCT ON (pt.id)
                    pt.id as tmpl_id,
                    po.id as po_id,
                    po.name as po_name,
                    po.partner_ref,
                    po.date_approve,
                    po.date_order,
                    pol.product_qty,
                    rp.name as partner_name
                FROM product_template pt
                JOIN product_product pp ON pp.product_tmpl_id = pt.id
                JOIN purchase_order_line pol ON pol.product_id = pp.id
                JOIN purchase_order po ON po.id = pol.order_id
                LEFT JOIN res_partner rp ON rp.id = po.partner_id
                WHERE pt.id IN %s
                  AND pol.product_qty > 0
                  AND po.state IN ('purchase', 'done')
                ORDER BY pt.id, po.date_order DESC, pol.id DESC
            """, [tuple(valid_ids)])
            po_done_map = {r['tmpl_id']: r for r in self.env.cr.dictfetchall()}

            # 2. Batch PO state khác bất kỳ (qty > 0) cho SP chưa có PO done
            missing_done = [i for i in valid_ids if i not in po_done_map]
            if missing_done:
                self.env.cr.execute("""
                    SELECT DISTINCT ON (pt.id)
                        pt.id as tmpl_id,
                        po.id as po_id,
                        po.name as po_name,
                        po.partner_ref,
                        po.date_approve,
                        po.date_order,
                        pol.product_qty,
                        rp.name as partner_name
                    FROM product_template pt
                    JOIN product_product pp ON pp.product_tmpl_id = pt.id
                    JOIN purchase_order_line pol ON pol.product_id = pp.id
                    JOIN purchase_order po ON po.id = pol.order_id
                    LEFT JOIN res_partner rp ON rp.id = po.partner_id
                    WHERE pt.id IN %s
                      AND pol.product_qty > 0
                    ORDER BY pt.id, po.date_order DESC, pol.id DESC
                """, [tuple(missing_done)])
                po_any_map = {r['tmpl_id']: r for r in self.env.cr.dictfetchall()}

            # 3. Batch Stock Moves fallback cho SP chưa từng có PO line nào
            missing_all_po = [i for i in missing_done if i not in po_any_map]
            if missing_all_po:
                self.env.cr.execute("""
                    SELECT DISTINCT ON (pt.id)
                        pt.id as tmpl_id,
                        sm.date,
                        coalesce(sm.quantity, sm.product_uom_qty) as qty,
                        sp.origin as pick_origin,
                        sm.origin as move_origin,
                        sp.name as pick_name
                    FROM product_template pt
                    JOIN product_product pp ON pp.product_tmpl_id = pt.id
                    JOIN stock_move sm ON sm.product_id = pp.id
                    LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
                    LEFT JOIN stock_picking_type spt ON spt.id = sm.picking_type_id
                    LEFT JOIN stock_location ld ON ld.id = sm.location_dest_id
                    LEFT JOIN stock_location ls ON ls.id = sm.location_id
                    WHERE pt.id IN %s
                      AND sm.state = 'done'
                      AND (spt.code = 'incoming' OR (ld.usage = 'internal' AND ls.usage != 'internal'))
                    ORDER BY pt.id, sm.date DESC, sm.id DESC
                """, [tuple(missing_all_po)])
                moves_map = {r['tmpl_id']: r for r in self.env.cr.dictfetchall()}

            # 4. Batch PO Báo giá (qty = 0 HOẶC state in draft, sent)
            self.env.cr.execute("""
                SELECT DISTINCT ON (pt.id)
                    pt.id as tmpl_id,
                    po.id as po_id,
                    po.name as po_name,
                    po.partner_ref,
                    po.date_approve,
                    po.date_order,
                    rp.name as partner_name
                FROM product_template pt
                JOIN product_product pp ON pp.product_tmpl_id = pt.id
                JOIN purchase_order_line pol ON pol.product_id = pp.id
                JOIN purchase_order po ON po.id = pol.order_id
                LEFT JOIN res_partner rp ON rp.id = po.partner_id
                WHERE pt.id IN %s
                  AND (pol.product_qty = 0 OR po.state IN ('draft', 'sent'))
                ORDER BY pt.id, po.date_order DESC, pol.id DESC
            """, [tuple(valid_ids)])
            quotes_map = {r['tmpl_id']: r for r in self.env.cr.dictfetchall()}

        for rec in self:
            real_id = rec._origin.id or (isinstance(rec.id, int) and rec.id)
            rec.last_purchase_date = False
            rec.last_purchase_code = False
            rec.last_quotation_date = False
            rec.last_quotation_code = False
            dt_purchase = False
            if not real_id:
                continue

            uom_str = rec.uom_id.name.lower() if rec.uom_id.name else "cái"

            # 1. Tính nhập gần nhất từ PO (done -> any) hoặc Stock Move
            po_info = po_done_map.get(real_id) or po_any_map.get(real_id)
            if po_info:
                code_name = po_info['po_name'] or "PO"
                partner_ref = po_info['partner_ref'].strip() if po_info['partner_ref'] else ""
                dt_purchase = po_info['date_approve'] or po_info['date_order']
                date_str = dt_purchase.strftime('%d/%m/%y') if dt_purchase else ''
                rec.last_purchase_date = dt_purchase.date() if dt_purchase else False
                qty = po_info['product_qty']

                if partner_ref:
                    po_display = f"{code_name} ({partner_ref})"
                else:
                    partner_name = po_info['partner_name'] or ""
                    short_partner = partner_name.split(" - ")[0].strip() if " - " in partner_name else partner_name[:5].strip()
                    if short_partner and date_str:
                        po_display = f"{code_name} ({short_partner} {date_str})"
                    elif date_str:
                        po_display = f"{code_name} {date_str}".strip()
                    else:
                        po_display = code_name

                rec.last_purchase_code = f"Nhập: {po_display} {qty:g} {uom_str}"
            elif real_id in moves_map:
                sm_info = moves_map[real_id]
                dt_purchase = sm_info['date']
                rec.last_purchase_date = dt_purchase.date() if dt_purchase else False
                date_str = dt_purchase.strftime('%d/%m/%y') if dt_purchase else ''
                qty = sm_info['qty'] or 0
                origin = sm_info['pick_origin'] or sm_info['move_origin'] or sm_info['pick_name'] or "Kho"
                rec.last_purchase_code = f"Nhập: {origin} {date_str} {qty:g} {uom_str}"

            # 2. Tính đơn báo giá gần nhất
            po_quote_info = quotes_map.get(real_id)
            po_quote_code = False
            po_quote_date = False
            dt_po_quote = False

            if po_quote_info:
                dt_po_quote = po_quote_info['date_approve'] or po_quote_info['date_order']
                po_quote_date = dt_po_quote.date() if dt_po_quote else False
                date_str = dt_po_quote.strftime('%d/%m/%y') if dt_po_quote else ''
                q_name = po_quote_info['po_name'] or "PO"
                q_pref = po_quote_info['partner_ref'].strip() if po_quote_info['partner_ref'] else ""

                if q_pref:
                    q_display = f"{q_name} ({q_pref})"
                else:
                    partner_name = po_quote_info['partner_name'] or ""
                    short_partner = partner_name.split(" - ")[0].strip() if " - " in partner_name else partner_name[:5].strip()
                    if short_partner and date_str:
                        q_display = f"{q_name} ({short_partner} {date_str})"
                    elif date_str:
                        q_display = f"{q_name} {date_str}".strip()
                    else:
                        q_display = q_name

                po_quote_code = f"Báo giá: {q_display}"

            # 3. So sánh ngày báo giá và ngày nhập hàng
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

    @api.model
    def _extract_oe_codes_from_name_and_sku(self, name="", brand_sku=""):
        """Trích xuất mã OE về duy nhất 1 dòng (không tách dấu /): ưu tiên brand_sku có sẵn, nếu trống thì lấy cặp dấu <...> trên tên SP"""
        import re
        if isinstance(brand_sku, str) and brand_sku.strip():
            return [brand_sku.strip()]
        if name:
            parts = [p.strip() for p in re.findall(r'<([^>]+)>', str(name)) if p.strip()]
            if parts:
                return [" | ".join(parts)]
        return []

    @api.onchange("description_sale")
    def _onchange_description_sale_sync_specs(self):
        if isinstance(self.description_sale, str) and self.description_sale.strip() and not (self.technical_specs and self.technical_specs.strip()):
            self.technical_specs = self.description_sale.strip()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('technical_specs'):
                notes = []
                for field_name in ('internal_notes', 'description_sale', 'description_purchase'):
                    raw = vals.get(field_name)
                    if isinstance(raw, str) and raw.strip() and raw.strip() not in notes:
                        notes.append(raw.strip())
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
        records = super().create(vals_list)
        records._auto_populate_oe_codes()
        return records

    def _auto_populate_oe_codes(self):
        """Tự động điền bảng OE. Code (1 dòng duy nhất, để trống cột Hãng) từ brand_sku hoặc <...> nếu sản phẩm chưa có mã OE"""
        oe_vals = []
        for rec in self:
            if not rec.oe_code_ids:
                for idx, code in enumerate(self._extract_oe_codes_from_name_and_sku(rec.name, rec.brand_sku)):
                    oe_vals.append({
                        'product_tmpl_id': rec.id,
                        'name': code,
                        'brand_id': False,
                        'sequence': (idx + 1) * 10,
                    })
        if oe_vals:
            self.env['qba.product.oe_code'].create(oe_vals)

    def action_open_bulk_edit_wizard(self):
        """Mở wizard cập nhật thuộc tính hàng loạt (chỉ dành cho Admin)"""
        if not (self.env.is_admin() or self.env.user.has_group('base.group_system')):
            raise UserError(_("Chức năng chỉnh sửa thuộc tính hàng loạt chỉ dành riêng cho Quản trị viên hệ thống (Admin)."))
        active_domain = self.env.context.get('active_domain')
        return {
            'name': _("Cập nhật thuộc tính sản phẩm hàng loạt (Admin)"),
            'type': 'ir.actions.act_window',
            'res_model': 'qba.product.bulk.edit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'product.template',
                'active_ids': self.ids,
                'default_product_tmpl_ids': [(6, 0, self.ids)],
                'default_filter_domain_repr': str(active_domain) if active_domain else False,
                'default_scope': 'selected' if self.ids else 'all',
            }
        }

    def _calculate_historical_stock_breakdown(self, variant_ids=None):
        """Tính toán chi tiết tồn kho chuẩn kế toán (quy đổi đúng ĐVT gốc, trừ hàng trả lại):
        SL tồn đầu kỳ = max(0, (Đã nhập - Trả NCC) - (Đã bán - Khách trả))"""
        self.ensure_one()
        if variant_ids is None:
            variant_ids = self.with_context(active_test=False).product_variant_ids.ids
        if not variant_ids:
            return 0.0, 0.0, 0.0

        company_domain = [('company_id', '=', self.company_id.id)] if self.company_id else []

        # 1. Đã nhập (PO đã xác nhận/hoàn tất hoặc dịch chuyển từ NCC vào kho, trừ hàng xuất trả NCC)
        po_lines = self.env['purchase.order.line'].sudo().search([
            ('product_id', 'in', variant_ids),
            ('order_id.state', 'in', ['purchase', 'done']),
        ] + company_domain)
        po_qty = sum(
            l.product_uom._compute_quantity(l.product_qty, l.product_id.uom_id)
            for l in po_lines
        )

        in_moves = self.env['stock.move'].sudo().search([
            ('product_id', 'in', variant_ids),
            ('location_id.usage', '=', 'supplier'),
            ('location_dest_id.usage', '=', 'internal'),
            ('state', '=', 'done'),
        ] + company_domain)
        in_move_qty = sum(
            m.product_uom._compute_quantity(m.quantity, m.product_id.uom_id)
            for m in in_moves
        )

        supplier_return_moves = self.env['stock.move'].sudo().search([
            ('product_id', 'in', variant_ids),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'supplier'),
            ('state', '=', 'done'),
        ] + company_domain)
        supplier_return_qty = sum(
            m.product_uom._compute_quantity(m.quantity, m.product_id.uom_id)
            for m in supplier_return_moves
        )
        qty_purchased = max(0.0, max(po_qty, in_move_qty) - supplier_return_qty)

        # 2. Đã bán (SO + POS hợp lệ hoặc dịch chuyển từ kho ra KH, trừ hàng khách trả lại)
        so_lines = self.env['sale.order.line'].sudo().search([
            ('product_id', 'in', variant_ids),
            ('order_id.state', 'in', ['sale', 'done']),
        ] + company_domain)
        so_qty = sum(
            l.product_uom._compute_quantity(l.product_uom_qty, l.product_id.uom_id)
            for l in so_lines
        )

        pos_lines = self.env['pos.order.line'].sudo().search([
            ('product_id', 'in', variant_ids),
            ('order_id.state', 'not in', ['draft', 'cancel']),
        ] + company_domain)
        pos_qty = sum(
            l.product_uom_id._compute_quantity(l.qty, l.product_id.uom_id)
            for l in pos_lines
        )

        out_moves = self.env['stock.move'].sudo().search([
            ('product_id', 'in', variant_ids),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'customer'),
            ('state', '=', 'done'),
        ] + company_domain)
        out_move_qty = sum(
            m.product_uom._compute_quantity(m.quantity, m.product_id.uom_id)
            for m in out_moves
        )

        customer_return_moves = self.env['stock.move'].sudo().search([
            ('product_id', 'in', variant_ids),
            ('location_id.usage', '=', 'customer'),
            ('location_dest_id.usage', '=', 'internal'),
            ('state', '=', 'done'),
        ] + company_domain)
        customer_return_qty = sum(
            m.product_uom._compute_quantity(m.quantity, m.product_id.uom_id)
            for m in customer_return_moves
        )
        qty_sold = max(0.0, max(so_qty + pos_qty, out_move_qty) - customer_return_qty)

        return qty_purchased, qty_sold, max(0.0, qty_purchased - qty_sold)

    def _calculate_historical_stock_qty(self):
        return self._calculate_historical_stock_breakdown()[2]

    def _auto_sync_stock_from_history(self):
        """Tự động ghi nhận bút toán Tồn đầu kỳ = max(0, Đã nhập - Đã bán) cho từng biến thể khi bật theo dõi kho"""
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', self.company_id.id or self.env.company.id)], limit=1
        )
        if not warehouse or not warehouse.lot_stock_id:
            return
        total_purchased = 0.0
        total_sold = 0.0
        total_target = 0.0
        for variant in self.with_context(active_test=False).product_variant_ids:
            qty_purchased, qty_sold, target_qty = self._calculate_historical_stock_breakdown(variant_ids=[variant.id])
            total_purchased += qty_purchased
            total_sold += qty_sold
            total_target += target_qty
            self.env['stock.quant'].with_context(
                inventory_mode=True,
                inventory_name=_("Tồn đầu kỳ theo lịch sử Mua/Bán")
            ).sudo().create({
                'product_id': variant.id,
                'location_id': warehouse.lot_stock_id.id,
                'inventory_quantity': target_qty,
            })._apply_inventory()
        self.sudo().message_post(
            body=_("Khai báo tồn kho đầu kỳ khi bật Theo dõi hàng tồn kho: Đã mua %g - Đã bán %g → Tồn đầu kỳ = %g.")
            % (total_purchased, total_sold, total_target)
        )

    def action_update_quantity_on_hand(self):
        """Khóa chỉnh tay tồn kho trên form sản phẩm (chỉ xem chỉ đọc; kiểm kê thực tế qua menu Tồn kho)."""
        action = self.action_open_quants()
        action['context'] = dict(action.get('context') or {}, create=False, edit=False, delete=False)
        return action

    def write(self, vals):
        is_admin = self.env.is_admin() or self.env.user.has_group('base.group_system')
        # KHÓA BẢO VỆ 1: Chặn tuyệt đối người dùng không phải Admin can thiệp vào is_storable hoặc uom_id
        if not is_admin:
            for field_name in ('is_storable', 'uom_id', 'uom_po_id'):
                if field_name in vals:
                    raise AccessError(_("BẢO VỆ PHÂN QUYỀN HỆ THỐNG:\n\nChỉ Quản trị viên hệ thống (Admin) mới có đặc quyền thay đổi tính chất tồn kho hoặc đơn vị tính của sản phẩm!"))

        target_storable = None
        target_uom_id = None
        target_uom_po_id = None

        if is_admin:
            if 'is_storable' in vals:
                target_storable = vals.pop('is_storable')
                # Chặn tắt theo dõi tồn kho nếu sản phẩm đang có số lượng tồn khác 0
                if target_storable is False:
                    for tmpl in self:
                        if tmpl.is_storable and tmpl.qty_available != 0:
                            raise UserError(_("CẢNH BÁO BẢO VỆ TỒN KHO:\n\nKhông thể tắt 'Theo dõi tồn kho' cho sản phẩm '%s' vì số lượng tồn kho hiện tại đang là %s. Vui lòng kiểm kê xuất kho về 0 trước khi tắt.") % (tmpl.display_name, tmpl.qty_available))

            if 'uom_id' in vals:
                target_uom_id = vals.pop('uom_id')
                # Chặn đổi ĐVT sang nhóm khác nếu đã có dịch chuyển kho
                if target_uom_id:
                    new_uom = self.env['uom.uom'].browse(target_uom_id)
                    for tmpl in self:
                        if tmpl.uom_id and tmpl.uom_id.category_id != new_uom.category_id:
                            has_moves = self.env['stock.move'].sudo().search_count([
                                ('product_id', 'in', tmpl.with_context(active_test=False).mapped('product_variant_ids').ids)
                            ])
                            if has_moves > 0:
                                raise UserError(_(
                                    "NGHIÊM CẤM ĐỔI ĐƠN VỊ TÍNH SAI NHÓM:\n\n"
                                    "Không thể đổi Đơn vị tính từ nhóm '%s' sang nhóm '%s' cho sản phẩm '%s' "
                                    "vì đã phát sinh lịch sử dịch chuyển kho!"
                                ) % (tmpl.uom_id.category_id.name, new_uom.category_id.name, tmpl.display_name))

            if 'uom_po_id' in vals:
                target_uom_po_id = vals.pop('uom_po_id')

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
                # Nếu người dùng xóa trống website_product_url: tự động ngắt liên kết và ngắt đồng bộ giá
                unlinks_to_notify = [tmpl.website_product_id for tmpl in self if tmpl.website_product_id and not self.env.context.get('skip_web_notify')]
                if unlinks_to_notify:
                    tmpl_model = self.browse()
                    self.env.cr.after('commit', lambda: [tmpl_model._notify_express_unlink(wid) for wid in unlinks_to_notify])
                vals.setdefault('website_product_id', False)
                vals.setdefault('website_product_slug', False)
                vals.setdefault('website_link_date', False)
                vals.setdefault('website_show_price', False)

        # Đồng bộ Mô tả bán hàng (description_sale) sang Mô tả SP (technical_specs) cho các bản ghi đang trống Mô tả SP
        sync_desc_tmpls = self.browse()
        raw_desc = vals.get('description_sale')
        if 'description_sale' in vals and isinstance(raw_desc, str) and raw_desc.strip() and not vals.get('technical_specs'):
            desc_val = raw_desc.strip()
            empty_specs = self.filtered(lambda t: not (t.technical_specs and t.technical_specs.strip()))
            if len(empty_specs) == len(self):
                vals['technical_specs'] = desc_val
            elif empty_specs:
                sync_desc_tmpls = empty_specs

        # Chỉ trích xuất lại mã OE trong write() khi nội dung <...> hoặc brand_sku thực sự thay đổi (tránh đẻ lại mã OE khách đã cố ý xóa)
        old_oe_sources = {}
        if ('name' in vals or 'brand_sku' in vals) and 'oe_code_ids' not in vals:
            old_oe_sources = {
                t.id: self._extract_oe_codes_from_name_and_sku(t.name, t.brand_sku)
                for t in self
            }

        res = super().write(vals)

        if sync_desc_tmpls:
            super(ProductTemplate, sync_desc_tmpls).write({'technical_specs': raw_desc.strip()})

        if old_oe_sources:
            changed_oe_tmpls = self.filtered(
                lambda t: not t.oe_code_ids and self._extract_oe_codes_from_name_and_sku(t.name, t.brand_sku) != old_oe_sources.get(t.id, [])
            )
            if changed_oe_tmpls:
                changed_oe_tmpls._auto_populate_oe_codes()

        # Thông báo cập nhật trạng thái liên kết & hiển thị giá sang Backend Express nếu có thay đổi
        web_fields_changed = {'website_product_id', 'website_show_price', 'list_price'} & set(vals.keys())
        if web_fields_changed and not self.env.context.get('skip_web_notify'):
            updates_to_notify = [
                (tmpl.id, tmpl.website_product_id, tmpl.website_show_price, tmpl.list_price)
                for tmpl in self if tmpl.website_product_id
            ]
            if updates_to_notify:
                def _do_notify_updates():
                    for tid, wid, show_p, lprice in updates_to_notify:
                        try:
                            self.browse(tid)._notify_express_update_display(wid, show_p, lprice)
                        except Exception:
                            pass
                self.env.cr.after('commit', _do_notify_updates)

        # Cập nhật an toàn các trường bị Odoo khóa cứng cho Admin
        if is_admin and (target_storable is not None or target_uom_id is not None or target_uom_po_id is not None):
            newly_storable = self.filtered(lambda t: not t.is_storable) if target_storable is True else self.browse()
            for tmpl in self:
                updates = []
                params = []
                if target_storable is not None:
                    updates.append("is_storable = %s")
                    params.append(bool(target_storable))
                if target_uom_id is not None:
                    updates.append("uom_id = %s")
                    params.append(target_uom_id)
                    # Đồng bộ uom_po_id nếu cần để không vi phạm ràng buộc nhóm đơn vị tính
                    if target_uom_po_id is not None:
                        updates.append("uom_po_id = %s")
                        params.append(target_uom_po_id)
                    else:
                        new_uom = self.env['uom.uom'].browse(target_uom_id)
                        if not tmpl.uom_po_id or tmpl.uom_po_id.category_id != new_uom.category_id:
                            updates.append("uom_po_id = %s")
                            params.append(target_uom_id)
                elif target_uom_po_id is not None:
                    updates.append("uom_po_id = %s")
                    params.append(target_uom_po_id)

                if updates:
                    params.append(tmpl.id)
                    query = f"UPDATE product_template SET {', '.join(updates)} WHERE id = %s"
                    self.env.cr.execute(query, tuple(params))

            # Invalidate cache sau khi cập nhật SQL trực tiếp
            fnames_to_invalidate = []
            if target_storable is not None:
                fnames_to_invalidate.append('is_storable')
            if target_uom_id is not None or target_uom_po_id is not None:
                fnames_to_invalidate.extend(['uom_id', 'uom_po_id', 'uom_name'])

            if fnames_to_invalidate:
                self.invalidate_recordset(fnames_to_invalidate)
                variants = self.with_context(active_test=False).mapped('product_variant_ids')
                if variants:
                    variants.invalidate_recordset([f for f in fnames_to_invalidate if f in variants._fields])

            # Tự động tính toán và đồng bộ tồn kho chỉ cho sản phẩm mới chuyển từ False -> True
            if newly_storable:
                for tmpl in newly_storable:
                    tmpl._auto_sync_stock_from_history()
                newly_storable.invalidate_recordset(['qty_available', 'virtual_available'])

        return res

    def _migrate_missing_oe_codes_sql(self):
        """Chuyển mã OE từ brand_sku hoặc <...> sang qba_product_oe_code (1 dòng, để trống Hãng) cho SP chưa có OE"""
        self.env.cr.execute("""
            SELECT pt.id,
                   coalesce(pt.name->>'vi_VN', pt.name->>'en_US', '') AS prod_name,
                   coalesce(pt.brand_sku, '') AS brand_sku
            FROM product_template pt
            WHERE (coalesce(pt.name->>'vi_VN', pt.name->>'en_US', '') ~ '<[^>]+>'
                   OR (pt.brand_sku IS NOT NULL AND trim(pt.brand_sku) != ''))
              AND NOT EXISTS (
                  SELECT 1 FROM qba_product_oe_code oe WHERE oe.product_tmpl_id = pt.id
              );
        """)
        rows = self.env.cr.fetchall()
        oe_vals = []
        for tmpl_id, prod_name, b_sku in rows:
            for idx, code in enumerate(self._extract_oe_codes_from_name_and_sku(prod_name, b_sku)):
                oe_vals.append((tmpl_id, code, None, (idx + 1) * 10))
        if oe_vals:
            self.env.cr.executemany("""
                INSERT INTO qba_product_oe_code (product_tmpl_id, name, brand_id, sequence, create_date, write_date, create_uid, write_uid)
                VALUES (%s, %s, %s, %s, NOW(), NOW(), 1, 1)
                ON CONFLICT (name, product_tmpl_id) DO NOTHING
            """, oe_vals)
        return [r[0] for r in rows]

    def _register_hook(self):
        """Chạy 1 lần duy nhất (guarded by ir.config_parameter): tạo trigram index, đồng bộ mô tả, mã OE, bảo hành và ảnh phụ"""
        super()._register_hook()
        try:
            icp = self.env['ir.config_parameter'].sudo()
            if icp.get_param('qba.trgm_search_indexes_v1') != '1':
                self.env.cr.execute("""
                    CREATE EXTENSION IF NOT EXISTS pg_trgm;
                    CREATE INDEX IF NOT EXISTS qba_pt_default_code_trgm_idx
                        ON product_template USING gin (default_code gin_trgm_ops);
                    CREATE INDEX IF NOT EXISTS qba_pt_oe_codes_display_trgm_idx
                        ON product_template USING gin (oe_codes_display gin_trgm_ops);
                    CREATE INDEX IF NOT EXISTS qba_oe_code_name_trgm_idx
                        ON qba_product_oe_code USING gin (name gin_trgm_ops);
                """)
                icp.set_param('qba.trgm_search_indexes_v1', '1')

            if icp.get_param('qba.oe_single_line_and_warranty_zero_v2') != '1':
                # 1. Reset toàn bộ bảo hành mặc định 90 ngày cũ về 0 ngày (Không bảo hành)
                self.env.cr.execute("""
                    UPDATE product_template
                    SET warranty_days = 0, warranty = 'Không bảo hành'
                    WHERE warranty_days IS NULL OR warranty_days = 90;
                """)

                # 2. Chỉ dọn các dòng OE đã auto-migrate (create_uid = 1, không có ghi chú) rồi gom lại về 1 dòng duy nhất, không tách /, để trống Hãng
                self.env.cr.execute("""
                    DELETE FROM qba_product_oe_code
                    WHERE create_uid = 1 AND (note IS NULL OR trim(note) = '')
                    RETURNING product_tmpl_id;
                """)
                deleted_tmpl_ids = {r[0] for r in self.env.cr.fetchall()}
                migrated_ids = self._migrate_missing_oe_codes_sql()
                all_affected = list(deleted_tmpl_ids | set(migrated_ids))
                if all_affected:
                    self.env.invalidate_all()
                    tmpls_v2 = self.browse(all_affected)
                    tmpls_v2._compute_oe_codes_display()
                    tmpls_v2._compute_oe_codes_list()
                    tmpls_v2.flush_recordset(['oe_codes_display', 'oe_codes_list'])
                icp.set_param('qba.oe_single_line_and_warranty_zero_v2', '1')

            if icp.get_param('qba.product_data_migrated_v1') == '1':
                return

            # Chuẩn hóa dấu , thành | trong bảng product_template
            self.env.cr.execute("""
                UPDATE product_template 
                SET oe_codes_display = REPLACE(REPLACE(oe_codes_display, ', ', ' | '), ',', ' | ') 
                WHERE oe_codes_display LIKE '%,%';
            """)

            # Gộp dữ liệu internal_notes, description_sale và description_purchase vào technical_specs nếu technical_specs chưa có
            self.env.cr.execute("""
                UPDATE product_template
                SET internal_notes = trim(
                    CASE
                        WHEN coalesce(trim(description_sale->>'vi_VN'), trim(description_sale->>'en_US'), '') != ''
                         AND coalesce(trim(description_purchase->>'vi_VN'), trim(description_purchase->>'en_US'), '') != ''
                         AND coalesce(trim(description_sale->>'vi_VN'), trim(description_sale->>'en_US'), '') != coalesce(trim(description_purchase->>'vi_VN'), trim(description_purchase->>'en_US'), '')
                        THEN coalesce(trim(description_sale->>'vi_VN'), trim(description_sale->>'en_US')) || E'\n' || coalesce(trim(description_purchase->>'vi_VN'), trim(description_purchase->>'en_US'))
                        ELSE coalesce(
                            NULLIF(trim(coalesce(description_sale->>'vi_VN', description_sale->>'en_US', '')), ''),
                            NULLIF(trim(coalesce(description_purchase->>'vi_VN', description_purchase->>'en_US', '')), '')
                        )
                    END
                )
                WHERE (internal_notes IS NULL OR trim(internal_notes) = '')
                  AND (
                      trim(coalesce(description_sale->>'vi_VN', description_sale->>'en_US', '')) != ''
                      OR trim(coalesce(description_purchase->>'vi_VN', description_purchase->>'en_US', '')) != ''
                  );

                UPDATE product_template
                SET technical_specs = CASE
                    WHEN (technical_specs IS NULL OR trim(technical_specs) = '') AND (internal_notes IS NOT NULL AND trim(internal_notes) != '') THEN trim(internal_notes)
                    WHEN (technical_specs IS NOT NULL AND trim(technical_specs) != '') AND (internal_notes IS NOT NULL AND trim(internal_notes) != '') AND position(trim(internal_notes) in technical_specs) = 0 THEN technical_specs || E'\n' || trim(internal_notes)
                    ELSE technical_specs
                END
                WHERE internal_notes IS NOT NULL AND trim(internal_notes) != '';

                UPDATE product_template
                SET technical_specs = trim(coalesce(description_sale->>'vi_VN', description_sale->>'en_US', ''))
                WHERE (technical_specs IS NULL OR trim(technical_specs) = '')
                  AND trim(coalesce(description_sale->>'vi_VN', description_sale->>'en_US', '')) != '';
            """)

            # Tự động chuyển mã từ brand_sku hoặc <...> sang bảng qba_product_oe_code (1 dòng duy nhất, để trống Hãng)
            migrated_v1_ids = self._migrate_missing_oe_codes_sql()
            if migrated_v1_ids:
                self.env.invalidate_all()
                tmpls = self.browse(migrated_v1_ids)
                tmpls._compute_oe_codes_display()
                tmpls._compute_oe_codes_list()
                tmpls.flush_recordset(['oe_codes_display', 'oe_codes_list'])

            # Chuẩn hóa bảo hành mặc định 0 ngày (Không bảo hành) nếu chưa thiết lập
            self.env.cr.execute("""
                UPDATE product_template
                SET warranty_days = 0
                WHERE warranty_days IS NULL;

                UPDATE product_template
                SET warranty = CASE
                    WHEN warranty_days > 0 THEN 'Bảo hành ' || warranty_days || ' ngày'
                    ELSE 'Không bảo hành'
                END
                WHERE warranty IS NULL OR (warranty_days = 0 AND warranty != 'Không bảo hành');
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
            icp.set_param('qba.product_data_migrated_v1', '1')
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
        default_fmt = self.env['qba.product.label.format'].search([('is_default', '=', True)], limit=1)
        if not default_fmt:
            default_fmt = self.env['qba.product.label.format'].search([], limit=1)
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
                'default_format_id': default_fmt.id if default_fmt else False,
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
            rec.website_show_price = False
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
        payload = {
            'odooProductId': None,
            'isOdooLinked': False,
            'showPrice': False,
            'unlink': True,
        }
        for ep in dedup:
            endpoint = f"{ep}/products/{web_product_id}/link-odoo"
            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=2.5)
                if resp.status_code == 200:
                    success = True
                    break
                elif resp.status_code == 401:
                    auth_error = True
                    break
            except Exception:
                pass
        return success, auth_error

    def _notify_express_update_display(self, web_product_id, show_price, price=None):
        """Gửi thông báo cập nhật trạng thái hiển thị giá (hoặc ẩn giá) tới Backend Express"""
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
        show_p = bool(show_price)
        payload = {
            'odooProductId': self.id,
            'showPrice': show_p,
            'price': float(price or 0.0) if show_p else 0.0,
            'priceText': f"{int(price):,} ₫" if (show_p and price) else "Liên hệ Báo giá",
        }

        for ep in dedup:
            endpoint = f"{ep}/products/{web_product_id}/link-odoo"
            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=2.5)
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False

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


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_update_quantity_on_hand(self):
        """Khóa chỉnh tay tồn kho trên form biến thể sản phẩm (chỉ xem chỉ đọc)."""
        action = self.action_open_quants()
        action['context'] = dict(action.get('context') or {}, create=False, edit=False, delete=False)
        return action




