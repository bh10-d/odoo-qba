# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont
import os
from reportlab.graphics.barcode.code128 import Code128
from .barcode_svg import generate_barcode_svg_string


class ProductLabelService:
    """Service class for generating product labels"""
    _FONT_CACHE = {}

    @classmethod
    def get_unicode_font(cls, size=18):
        """Get font that supports Vietnamese Unicode with in-memory caching"""
        if size in cls._FONT_CACHE:
            return cls._FONT_CACHE[size]

        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            'C:/Windows/Fonts/arial.ttf',
            '/System/Library/Fonts/Arial.ttf',
        ]
        loaded_font = None
        for path in font_paths:
            try:
                if os.path.exists(path):
                    loaded_font = ImageFont.truetype(path, size)
                    break
            except Exception:
                continue

        if not loaded_font:
            loaded_font = ImageFont.load_default()

        cls._FONT_CACHE[size] = loaded_font
        return loaded_font

    @staticmethod
    def generate_barcode_image(value, symbology='Code128', width=480, height=80):
        """Generate barcode image using pure PIL with Code128 bar pattern (no external C renderPM dependency)"""
        if not value:
            return None
        val_str = str(value).strip()
        if not val_str:
            return None

        # Code128 natively supports standard ASCII
        try:
            val_str.encode('ascii')
        except UnicodeEncodeError:
            return None

        try:
            bc = Code128(val_str, barHeight=height, barWidth=2)
            bc._calculate()
            raw_w = int(bc._width)
            raw_h = int(bc.barHeight)
            img = Image.new('RGBA', (raw_w, raw_h), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            oa, oA = ord('a') - 1, ord('A') - 1
            left = 0
            for c in bc.decomposed:
                oc = ord(c)
                if 'a' <= c <= 'z':
                    left += (oc - oa) * bc.barWidth
                elif 'A' <= c <= 'Z':
                    w = (oc - oA) * bc.barWidth
                    draw.rectangle([left, 0, left + w - 1, raw_h], fill=(0, 0, 0, 255))
                    left += w

            # Scale to requested target width if different
            if width and width != raw_w:
                img = img.resize((int(width), int(height)), Image.Resampling.NEAREST)
            return img
        except Exception as e:
            return None

    @classmethod
    def generate_label_image(cls, product, supplier_product_code=None, nhap_date=None, dinh_luong=None, custom_name=None, format_id=None):
        """Generate product label image with high-contrast, perfectly aligned layout matching format_id if provided"""
        if format_id:
            W = int(format_id.width_mm * 10)
            H = int(format_id.height_mm * 10)
            P = max(int(W * 0.04), 10)
            border_radius = max(int(format_id.border_radius_mm * 10), 0)
            border_color = format_id.border_color or "#e43c24"
            border_width = max(int(format_id.border_width_mm * 10), 2)
            font_product_size = max(int(format_id.product_name_font_size_pt * 3.4), 16)
            font_meta_size = max(int(format_id.brand_font_size_pt * 3.4), 14)
            font_small_size = max(int(format_id.sku_font_size_pt * 3.4), 12)
            sep_color = format_id.separator_color or "#e43c24"
            sep_height = max(int(format_id.separator_thickness_mm * 10), 2)
        else:
            W, H = 1000, 700
            P = 40  # padding
            border_radius = 32
            border_color = "#e43c24"
            border_width = 6
            font_product_size = 38
            font_meta_size = 28
            font_small_size = 24
            sep_color = "#e43c24"
            sep_height = 6

        label = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(label)

        # Fonts
        font_product = cls.get_unicode_font(font_product_size)
        font = cls.get_unicode_font(font_meta_size)
        font_small = cls.get_unicode_font(font_small_size)

        # Viền bo góc màu đỏ cam QBA
        mask = Image.new("L", (W, H), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (W - 1, H - 1)], radius=border_radius, fill=255)
        border = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border)
        border_draw.rounded_rectangle(
            [(border_width // 2, border_width // 2), (W - 1 - border_width // 2, H - 1 - border_width // 2)],
            radius=border_radius,
            outline=border_color,
            width=border_width
        )

        # --- 1. PHẦN ĐẦU (Header) ---
        # Logo QBA (trái)
        logo_x = P
        logo_y = P
        logo_w, logo_h = 0, 0
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'src', 'img', 'logo.png')
        target_logo_h = int(format_id.logo_height_mm * 10) if format_id else 110
        target_logo_w = int(target_logo_h * 2.5)
        if os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                logo_img.thumbnail((target_logo_w, target_logo_h), Image.Resampling.LANCZOS)
                label.paste(logo_img, (logo_x, logo_y), logo_img)
                logo_w, logo_h = logo_img.size
            except Exception:
                logo_w, logo_h = target_logo_w, target_logo_h
                draw.rectangle([logo_x, logo_y, logo_x + logo_w, logo_y + logo_h], outline='black', width=2)
                draw.text((logo_x + 10, logo_y + 10), 'QBA', fill='black', font=font_product)
        else:
            logo_w, logo_h = target_logo_w, target_logo_h
            draw.rectangle([logo_x, logo_y, logo_x + logo_w, logo_y + logo_h], outline='black', width=2)
            draw.text((logo_x + 10, logo_y + 10), 'QBA', fill='black', font=font_product)

        # Barcode & mã nhà cung cấp (phải)
        supplier_code_str = (supplier_product_code or '').strip()
        # Fallback to seller_ids if not explicitly passed
        if not supplier_code_str and product.seller_ids:
            first_seller = product.seller_ids.filtered(lambda s: s.product_code)[:1]
            if first_seller:
                supplier_code_str = (first_seller.product_code or '').strip()

        barcode_h = int(format_id.supplier_barcode_height_mm * 10) if format_id else 75
        barcode_w = max(int(W * 0.42), 120)
        barcode_img = cls.generate_barcode_image(supplier_code_str, width=barcode_w, height=barcode_h) if supplier_code_str else None
        barcode_x = W - P - (barcode_img.size[0] if barcode_img else barcode_w)
        barcode_y = logo_y

        if barcode_img:
            label.paste(barcode_img, (barcode_x, barcode_y), barcode_img)
            t_bbox = font_small.getbbox(supplier_code_str)
            text_w = t_bbox[2] - t_bbox[0]
            text_x = barcode_x + (barcode_img.size[0] - text_w) // 2
            draw.text((text_x, barcode_y + barcode_h + 3), supplier_code_str, font=font_small, fill="black")
        elif supplier_code_str:
            # Nếu không tạo được vạch (vd có ký tự đặc biệt), vẫn in rõ mã số
            t_bbox = font.getbbox(f"Mã NCC: {supplier_code_str}")
            text_w = t_bbox[2] - t_bbox[0]
            draw.text((W - P - text_w, barcode_y + 20), f"Mã NCC: {supplier_code_str}", font=font, fill="black")

        # --- 2. PHẦN TÊN SẢN PHẨM (Middle) ---
        product_name = custom_name or product.name or ''
        max_text_width = W - 2 * P
        max_lines = format_id.product_name_max_lines if format_id else 3

        # Tự động co cỡ chữ nếu tên dài để vừa đủ max_lines mà không bị nuốt mất từ
        curr_font_size = font_product_size
        wrapped_lines = []
        while curr_font_size >= 14:
            font_product = cls.get_unicode_font(curr_font_size)
            words = product_name.split()
            wrapped_lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                try:
                    line_w = font_product.getlength(test_line)
                except Exception:
                    line_w = len(test_line) * (curr_font_size * 0.5)
                if line_w <= max_text_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        wrapped_lines.append(word)
                        current_line = []
            if current_line:
                wrapped_lines.append(' '.join(current_line))
            if len(wrapped_lines) <= max_lines or curr_font_size <= 14:
                break
            curr_font_size -= 2

        line_bbox = font_product.getbbox("Ay")
        line_height = (line_bbox[3] - line_bbox[1]) + max(int(P * 0.35), 6)

        top_elements_bottom = max(logo_y + logo_h, barcode_y + (barcode_h + 24 if supplier_code_str else 0))
        product_y = top_elements_bottom + max(int(P * 0.4), 8)

        final_lines = wrapped_lines[:max_lines]
        for i, line in enumerate(final_lines):
            draw.text((P, product_y + i * line_height), line, font=font_product, fill="black")

        text_end_y = product_y + len(final_lines) * line_height

        # --- 3. ĐƯỜNG PHÂN CÁCH (Separator Line) ---
        sep_y = max(text_end_y + max(int(P * 0.3), 6), int(H * 0.50))
        sep_y = min(sep_y, int(H * 0.65))
        line_padding = border_width + 5
        draw.rectangle([(line_padding, sep_y), (W - line_padding, sep_y + sep_height)], fill=sep_color)

        # --- 4. PHẦN DƯỚI (Bottom Section) ---
        meta_y = sep_y + sep_height + max(int(P * 0.25), 4)
        final_nhap_date = nhap_date or product.last_purchase_date
        final_dinh_luong = dinh_luong or (f"1 {product.uom_id.name}".strip() if product.uom_id else "")

        if H <= 350:
            # Đối với tem nhỏ (chiều cao <= 35mm), để Ngày nhập & Định lượng trên cùng 1 dòng
            meta_right_parts = []
            if final_nhap_date:
                meta_right_parts.append(final_nhap_date.strftime('%d/%m/%Y'))
            if final_dinh_luong:
                meta_right_parts.append(f"ĐL: {final_dinh_luong}")
            meta_right_str = ' | '.join(meta_right_parts)
            if meta_right_str:
                r_bbox = font.getbbox(meta_right_str)
                draw.text((W - P - (r_bbox[2] - r_bbox[0]), meta_y), meta_right_str, font=font, fill="black")
            if product.brand_id:
                draw.text((P, meta_y), f"Hãng: {product.brand_id.name}", font=font, fill="black")
            meta_bottom_y = meta_y + font_meta_size + 4
        else:
            # Đối với tem trung / lớn (75x50, 100x70mm), xếp Ngày nhập & Định lượng thành 2 dòng
            curr_y = meta_y
            if final_nhap_date:
                nhap_text = final_nhap_date.strftime('%d/%m/%Y')
                nhap_bbox = font.getbbox(nhap_text)
                draw.text((W - P - (nhap_bbox[2] - nhap_bbox[0]), curr_y), nhap_text, font=font, fill="black")
                curr_y += (nhap_bbox[3] - nhap_bbox[1]) + 4
            if final_dinh_luong:
                dl_text = f"ĐL: {final_dinh_luong}"
                dl_bbox = font.getbbox(dl_text)
                draw.text((W - P - (dl_bbox[2] - dl_bbox[0]), curr_y), dl_text, font=font, fill="black")
                curr_y += (dl_bbox[3] - dl_bbox[1]) + 4
            if product.brand_id:
                draw.text((P, meta_y), f"Hãng: {product.brand_id.name}", font=font, fill="black")
            meta_bottom_y = max(curr_y, meta_y + font_meta_size + 4)

        # Mã vạch SKU sản phẩm (Căn giữa tuyệt đối phía dưới meta_bottom_y, không bao giờ bị đè)
        sku_val = (product.default_code or '').strip()
        bottom_area_start = meta_bottom_y + max(int(P * 0.15), 3)
        bottom_area_end = H - border_width - max(int(P * 0.15), 4)
        avail_code_h = bottom_area_end - bottom_area_start

        if sku_val and avail_code_h > 20:
            code_w = max(int(W * 0.58), 160)
            target_code_h = int(format_id.sku_barcode_height_mm * 10) if format_id else 80
            code_h = min(target_code_h, max(avail_code_h - 26, 22))
            code_img = cls.generate_barcode_image(sku_val, width=code_w, height=code_h)
            total_code_h = code_h + 24
            code_y = bottom_area_start + max((avail_code_h - total_code_h) // 2, 0)
            code_x = (W - code_w) // 2
            if code_img:
                label.paste(code_img, (code_x, code_y), code_img)
                t_bbox = font_small.getbbox(sku_val)
                t_w = t_bbox[2] - t_bbox[0]
                t_x = code_x + (code_w - t_w) // 2
                draw.text((t_x, code_y + code_h + 3), sku_val, font=font_small, fill="black")
            else:
                t_bbox = font_product.getbbox(sku_val)
                t_w = t_bbox[2] - t_bbox[0]
                t_x = (W - t_w) // 2
                draw.text((t_x, code_y + 10), sku_val, font=font_product, fill="black")

        # Áp viền bo góc lên tem
        label = Image.composite(label, Image.new("RGB", (W, H), "white"), mask)
        label = Image.alpha_composite(label.convert("RGBA"), border)

        # Convert to PNG
        buffer = BytesIO()
        label.convert("RGB").save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue())


class ProductLabelWizard(models.TransientModel):
    _name = 'qba.product.label.wizard'
    _description = 'Wizard tạo tem sản phẩm QBA'

    product_id = fields.Many2one('product.template', string='Sản phẩm', required=True)
    default_code = fields.Char(related='product_id.default_code', string='Mã SKU sản phẩm', readonly=True)
    custom_name = fields.Char(string='Tên sản phẩm in trên tem')
    supplier_product_code = fields.Many2one(
        'product.supplierinfo',
        string='Chọn từ Nhà cung cấp',
        domain="[('product_tmpl_id', '=', product_id)]"
    )
    supplier_code = fields.Char(string='Mã NCC / Mã vạch phụ', help="Mã hàng NCC hoặc mã vạch phụ in góc trên bên phải")
    nhap_date = fields.Date(string='Ngày nhập')
    dinh_luong = fields.Char(string='Định lượng', help="Ví dụ: 1 Cái, 1 Bộ, 1 Chiếc...")

    # Cấu hình Mẫu in tem & Khổ in
    format_id = fields.Many2one('qba.product.label.format', string='Mẫu & Khổ in tem', required=True)
    qty_to_print = fields.Integer(string='Số lượng tem in', default=1, required=True)

    # Tùy biến nhanh mẫu in tem ngay trên Wizard (Proxy qua format_id)
    format_name = fields.Char(related='format_id.name', string='Tên mẫu tem', readonly=False)
    format_width_mm = fields.Float(related='format_id.width_mm', string='Chiều rộng (mm)', readonly=False)
    format_height_mm = fields.Float(related='format_id.height_mm', string='Chiều cao (mm)', readonly=False)
    format_show_logo = fields.Boolean(related='format_id.show_logo', string='Hiện Logo', readonly=False)
    format_logo_height_mm = fields.Float(related='format_id.logo_height_mm', string='Chiều cao Logo (mm)', readonly=False)
    format_show_supplier_code = fields.Boolean(related='format_id.show_supplier_code', string='Hiện Mã NCC', readonly=False)
    format_supplier_code_display = fields.Selection(related='format_id.supplier_code_display', string='Kiểu hiển thị Mã NCC', readonly=False)
    format_supplier_barcode_height_mm = fields.Float(related='format_id.supplier_barcode_height_mm', string='Chiều cao Barcode NCC (mm)', readonly=False)
    format_supplier_font_size_pt = fields.Float(related='format_id.supplier_font_size_pt', string='Cỡ chữ Mã NCC (pt)', readonly=False)
    format_show_product_name = fields.Boolean(related='format_id.show_product_name', string='Hiện Tên SP', readonly=False)
    format_product_name_font_size_pt = fields.Float(related='format_id.product_name_font_size_pt', string='Cỡ chữ Tên SP (pt)', readonly=False)
    format_product_name_bold = fields.Boolean(related='format_id.product_name_bold', string='In đậm Tên SP', readonly=False)
    format_product_name_align = fields.Selection(related='format_id.product_name_align', string='Căn lề Tên SP', readonly=False)
    format_product_name_max_lines = fields.Integer(related='format_id.product_name_max_lines', string='Số dòng Tên SP tối đa', readonly=False)
    format_show_separator_line = fields.Boolean(related='format_id.show_separator_line', string='Hiện đường kẻ', readonly=False)
    format_separator_color = fields.Char(related='format_id.separator_color', string='Màu đường kẻ', readonly=False)
    format_separator_thickness_mm = fields.Float(related='format_id.separator_thickness_mm', string='Độ dày đường kẻ (mm)', readonly=False)
    format_show_brand = fields.Boolean(related='format_id.show_brand', string='Hiện Hãng', readonly=False)
    format_brand_font_size_pt = fields.Float(related='format_id.brand_font_size_pt', string='Cỡ chữ Hãng (pt)', readonly=False)
    format_show_nhap_date = fields.Boolean(related='format_id.show_nhap_date', string='Hiện Ngày nhập', readonly=False)
    format_nhap_date_font_size_pt = fields.Float(related='format_id.nhap_date_font_size_pt', string='Cỡ chữ Ngày nhập (pt)', readonly=False)
    format_show_dinh_luong = fields.Boolean(related='format_id.show_dinh_luong', string='Hiện Định lượng', readonly=False)
    format_dinh_luong_font_size_pt = fields.Float(related='format_id.dinh_luong_font_size_pt', string='Cỡ chữ Định lượng (pt)', readonly=False)
    format_show_sku_barcode = fields.Boolean(related='format_id.show_sku_barcode', string='Hiện Barcode SKU', readonly=False)
    format_sku_barcode_height_mm = fields.Float(related='format_id.sku_barcode_height_mm', string='Chiều cao Barcode SKU (mm)', readonly=False)
    format_sku_font_size_pt = fields.Float(related='format_id.sku_font_size_pt', string='Cỡ chữ Barcode SKU (pt)', readonly=False)
    format_border_style = fields.Selection(related='format_id.border_style', string='Kiểu viền tem', readonly=False)
    format_border_color = fields.Char(related='format_id.border_color', string='Màu viền tem', readonly=False)
    format_border_width_mm = fields.Float(related='format_id.border_width_mm', string='Độ dày viền (mm)', readonly=False)
    format_border_radius_mm = fields.Float(related='format_id.border_radius_mm', string='Bo góc viền (mm)', readonly=False)

    is_system_admin = fields.Boolean(string='Có quyền cấu hình tem', default=True)
    preview_html = fields.Html(string='Xem trước tem', compute='_compute_preview_html', sanitize=False)

    @api.depends_context('uid')
    def _compute_is_system_admin(self):
        is_admin = self.env.user.has_group('base.group_system')
        for rec in self:
            rec.is_system_admin = is_admin

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        product_id = res.get('product_id') or self.env.context.get('default_product_id')
        if product_id:
            product = self.env['product.template'].browse(product_id)
            if 'custom_name' in fields_list and not res.get('custom_name'):
                res['custom_name'] = product.name
            if 'nhap_date' in fields_list and not res.get('nhap_date'):
                res['nhap_date'] = product.last_purchase_date or fields.Date.context_today(self)
            if 'dinh_luong' in fields_list and not res.get('dinh_luong'):
                uom_name = product.uom_id.name if product.uom_id else ''
                res['dinh_luong'] = f"1 {uom_name}".strip() if uom_name else "1 Cái"
            first_seller = product.seller_ids.filtered(lambda s: s.product_code)[:1]
            if 'supplier_product_code' in fields_list and not res.get('supplier_product_code'):
                if first_seller:
                    res['supplier_product_code'] = first_seller.id
            if 'supplier_code' in fields_list and not res.get('supplier_code'):
                if first_seller and first_seller.product_code:
                    res['supplier_code'] = first_seller.product_code

        if 'format_id' in fields_list and not res.get('format_id'):
            default_format = self.env['qba.product.label.format'].search([('is_default', '=', True)], limit=1)
            if not default_format:
                default_format = self.env['qba.product.label.format'].search([], limit=1)
            if default_format:
                res['format_id'] = default_format.id

        return res

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.custom_name = self.product_id.name
            first_seller = self.product_id.seller_ids.filtered(lambda s: s.product_code)[:1]
            self.supplier_product_code = first_seller.id if first_seller else False
            self.supplier_code = first_seller.product_code if first_seller else ''
            self.nhap_date = self.product_id.last_purchase_date or fields.Date.context_today(self)
            uom_name = self.product_id.uom_id.name if self.product_id.uom_id else ''
            self.dinh_luong = f"1 {uom_name}".strip() if uom_name else "1 Cái"

    @api.onchange('supplier_product_code')
    def _onchange_supplier_product_code(self):
        if self.supplier_product_code and self.supplier_product_code.product_code:
            self.supplier_code = self.supplier_product_code.product_code

    def get_barcode_svg(self, value, height_mm=8.0, max_width_mm=None, show_text=False, font_size_pt=7.5):
        """Helper for QWeb report to render vector SVG barcode with auto-scaling"""
        if not max_width_mm and self.format_id:
            max_width_mm = self.format_id.width_mm * 0.85
        return generate_barcode_svg_string(
            value,
            max_width_mm=max_width_mm or 70.0,
            height_mm=height_mm,
            show_text=show_text,
            font_size_pt=font_size_pt
        )

    def get_logo_data(self):
        """Helper to get base64 data URI of logo"""
        self.ensure_one()
        if self.format_id and self.format_id.custom_logo:
            return f"data:image/png;base64,{self.format_id.custom_logo.decode('utf-8')}"
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'src', 'img', 'logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{b64}"
        return None

    @api.depends(
        'product_id', 'custom_name', 'supplier_code', 'nhap_date', 'dinh_luong', 'format_id',
        'format_width_mm', 'format_height_mm', 'format_show_logo', 'format_logo_height_mm',
        'format_show_supplier_code', 'format_supplier_code_display', 'format_supplier_barcode_height_mm', 'format_supplier_font_size_pt',
        'format_show_product_name', 'format_product_name_font_size_pt', 'format_product_name_bold', 'format_product_name_align', 'format_product_name_max_lines',
        'format_show_separator_line', 'format_separator_color', 'format_separator_thickness_mm',
        'format_show_brand', 'format_brand_font_size_pt', 'format_show_nhap_date', 'format_nhap_date_font_size_pt', 'format_show_dinh_luong', 'format_dinh_luong_font_size_pt',
        'format_show_sku_barcode', 'format_sku_barcode_height_mm', 'format_sku_font_size_pt',
        'format_border_style', 'format_border_color', 'format_border_width_mm', 'format_border_radius_mm'
    )
    def _compute_preview_html(self):
        for rec in self:
            fmt = rec.format_id
            if not fmt:
                rec.preview_html = "<div class='text-muted text-center p-3'>Chưa chọn mẫu tem</div>"
                continue

            supp_code = (rec.supplier_code or '').strip()
            sku_code = (rec.default_code or (rec.product_id.default_code if rec.product_id else '') or '').strip()
            prod_name = rec.custom_name or (rec.product_id.name if rec.product_id else '')
            brand_name = rec.product_id.brand_id.name if rec.product_id and rec.product_id.brand_id else ''
            nhap_date_str = rec.nhap_date.strftime('%d/%m/%Y') if rec.nhap_date else ''
            dl_str = rec.dinh_luong or ''

            # Use wizard proxy values if set, fallback to fmt
            width_mm = rec.format_width_mm or fmt.width_mm
            height_mm = rec.format_height_mm or fmt.height_mm
            max_sku_w = width_mm * 0.82
            max_supp_w = width_mm * 0.45

            show_supp = rec.format_show_supplier_code
            supp_disp = rec.format_supplier_code_display
            supp_svg = generate_barcode_svg_string(supp_code, max_width_mm=max_supp_w, height_mm=rec.format_supplier_barcode_height_mm, show_text=False) if (supp_code and show_supp and supp_disp in ('barcode_and_text', 'barcode_only')) else None
            sku_svg = generate_barcode_svg_string(sku_code, max_width_mm=max_sku_w, height_mm=rec.format_sku_barcode_height_mm, show_text=False) if (sku_code and rec.format_show_sku_barcode) else None
            logo_uri = rec.get_logo_data()

            border_css = "border: none;"
            if rec.format_border_style == 'rounded':
                border_css = f"border: {rec.format_border_width_mm:.1f}mm solid {rec.format_border_color}; border-radius: {rec.format_border_radius_mm:.1f}mm;"
            elif rec.format_border_style == 'square':
                border_css = f"border: {rec.format_border_width_mm:.1f}mm solid {rec.format_border_color}; border-radius: 0;"

            pad_mm = 0.8 if width_mm <= 35.0 else (1.2 if width_mm <= 50.0 else (1.8 if width_mm <= 75.0 else 2.2))

            logo_html = ''
            if rec.format_show_logo and logo_uri:
                logo_html = f'<img src="{logo_uri}" style="height: {rec.format_logo_height_mm:.1f}mm; max-width: 100%; object-fit: contain;" alt="Logo"/>'

            supp_section_html = ''
            if supp_code and show_supp:
                if supp_disp in ('barcode_and_text', 'barcode_only'):
                    text_row = f'<tr><td style="text-align: center; font-size: {rec.format_supplier_font_size_pt:.1f}pt; font-weight: 600; line-height: 1.1; margin-top: 0.2mm; color: #000000;">{supp_code}</td></tr>' if supp_disp == 'barcode_and_text' else ''
                    supp_section_html = f"""
                        <table align="right" style="margin-left: auto; border-collapse: collapse; border-spacing: 0;">
                            <tr>
                                <td style="text-align: center; vertical-align: middle; padding: 0;">
                                    <div style="height: {rec.format_supplier_barcode_height_mm:.1f}mm; display: inline-block;">
                                        {supp_svg or ''}
                                    </div>
                                </td>
                            </tr>
                            {text_row}
                        </table>
                    """
                elif supp_disp == 'text_only':
                    supp_section_html = f'<div style="font-size: {rec.format_supplier_font_size_pt:.1f}pt; font-weight: bold; color: #000000; line-height: 1.1;">Mã NCC: {supp_code}</div>'

            prod_name_html = ''
            if rec.format_show_product_name and prod_name:
                bold_val = 'bold' if rec.format_product_name_bold else 'normal'
                align_val = rec.format_product_name_align or 'left'
                max_lines = rec.format_product_name_max_lines or 3
                prod_name_html = f"""
                    <div style="width: 100%; margin-top: 0.8mm; line-height: 1.25; color: #000000; word-break: break-word; overflow: hidden; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: {max_lines}; max-height: {max_lines * 1.25}em; font-size: {rec.format_product_name_font_size_pt:.1f}pt; font-weight: {bold_val}; text-align: {align_val};">
                        {prod_name}
                    </div>
                """

            sep_html = ''
            if rec.format_show_separator_line:
                sep_html = f'<div style="width: 100%; height: {rec.format_separator_thickness_mm:.1f}mm; background-color: {rec.format_separator_color}; margin-bottom: 0.8mm;"></div>'

            meta_table_html = ''
            if rec.format_show_brand or rec.format_show_nhap_date or rec.format_show_dinh_luong:
                brand_part = f'<div style="font-size: {rec.format_brand_font_size_pt:.1f}pt; color: #000000;">Hãng: <b>{brand_name}</b></div>' if (rec.format_show_brand and brand_name) else ''
                if height_mm <= 35.0:
                    meta_right_parts = []
                    if rec.format_show_nhap_date and nhap_date_str:
                        meta_right_parts.append(nhap_date_str)
                    if rec.format_show_dinh_luong and dl_str:
                        meta_right_parts.append(f"ĐL: <b>{dl_str}</b>")
                    meta_right_str = ' | '.join(meta_right_parts)
                    right_part = f'<div style="font-size: {rec.format_nhap_date_font_size_pt:.1f}pt; color: #000000; white-space: nowrap;">{meta_right_str}</div>' if meta_right_str else ''
                else:
                    date_part = f'<div style="font-size: {rec.format_nhap_date_font_size_pt:.1f}pt; color: #000000;">{nhap_date_str}</div>' if (rec.format_show_nhap_date and nhap_date_str) else ''
                    dl_part = f'<div style="font-size: {rec.format_dinh_luong_font_size_pt:.1f}pt; color: #000000;">ĐL: <b>{dl_str}</b></div>' if (rec.format_show_dinh_luong and dl_str) else ''
                    right_part = f'{date_part}{dl_part}'

                meta_table_html = f"""
                    <table style="width: 100%; border-collapse: collapse; border-spacing: 0; color: #000000;">
                        <tr>
                            <td style="width: 50%; text-align: left; vertical-align: middle; padding: 0;">
                                {brand_part}
                            </td>
                            <td style="width: 50%; text-align: right; vertical-align: middle; line-height: 1.2; padding: 0;">
                                {right_part}
                            </td>
                        </tr>
                    </table>
                """

            sku_section_html = ''
            if rec.format_show_sku_barcode and sku_code:
                sku_section_html = f"""
                    <div style="display: inline-block; text-align: center;">
                        {sku_svg or ''}
                    </div>
                    <div style="font-weight: bold; letter-spacing: 0.5px; margin-top: 0.3mm; color: #000000; font-size: {rec.format_sku_font_size_pt:.1f}pt;">
                        {sku_code}
                    </div>
                """

            preview = f"""
            <div style="background-color: #f1f3f5; padding: 24px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; overflow-x: auto;">
                <div style="font-size: 12px; color: #6c757d; margin-bottom: 8px; font-weight: 500;">
                    <i class="fa fa-eye me-1"></i>Xem trước tem thực tế ({width_mm:.0f} x {height_mm:.0f} mm) - 100% WYSIWYG chuẩn in nhiệt
                </div>
                <div style="width: {width_mm:.1f}mm; height: {height_mm:.1f}mm; background: #ffffff; {border_css} padding: {pad_mm}mm; box-sizing: border-box; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.12); font-family: Arial, 'DejaVu Sans', 'Helvetica Neue', sans-serif;">
                    <table style="width: 100%; height: 100%; border-collapse: collapse; border-spacing: 0;">
                        <!-- 1. TOP ROW (50% height): Header & Product Name -->
                        <tr style="height: 50%; vertical-align: top;">
                            <td style="vertical-align: top; padding: 0;">
                                <table style="width: 100%; border-collapse: collapse; border-spacing: 0;">
                                    <tr>
                                        <td style="text-align: left; vertical-align: middle; padding: 0;">
                                            {logo_html}
                                        </td>
                                        <td style="text-align: right; vertical-align: middle; padding: 0;">
                                            {supp_section_html}
                                        </td>
                                    </tr>
                                </table>
                                {prod_name_html}
                            </td>
                        </tr>

                        <!-- 2. MIDDLE ROW (18% height): Separator line & Meta Details -->
                        <tr style="height: 18%; vertical-align: top;">
                            <td style="vertical-align: top; padding: 0;">
                                {sep_html}
                                {meta_table_html}
                            </td>
                        </tr>

                        <!-- 3. BOTTOM ROW (32% height): SKU Barcode centered -->
                        <tr style="height: 32%; vertical-align: middle; text-align: center;">
                            <td style="vertical-align: middle; text-align: center; padding: 0;">
                                {sku_section_html}
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
            """
            rec.preview_html = preview

    @api.onchange(
        'format_id', 'custom_name', 'supplier_code', 'nhap_date', 'dinh_luong',
        'format_width_mm', 'format_height_mm', 'format_show_logo', 'format_logo_height_mm',
        'format_show_supplier_code', 'format_supplier_code_display', 'format_supplier_barcode_height_mm', 'format_supplier_font_size_pt',
        'format_show_product_name', 'format_product_name_font_size_pt', 'format_product_name_bold', 'format_product_name_align', 'format_product_name_max_lines',
        'format_show_separator_line', 'format_separator_color', 'format_separator_thickness_mm',
        'format_show_brand', 'format_brand_font_size_pt', 'format_show_nhap_date', 'format_nhap_date_font_size_pt', 'format_show_dinh_luong', 'format_dinh_luong_font_size_pt',
        'format_show_sku_barcode', 'format_sku_barcode_height_mm', 'format_sku_font_size_pt',
        'format_border_style', 'format_border_color', 'format_border_width_mm', 'format_border_radius_mm'
    )
    def _onchange_format_layout_fields(self):
        self._compute_preview_html()

    def _generate_label_image_for_product(self):
        """Generate label image (PNG) matching current format and data"""
        self.ensure_one()
        supplier_code = (self.supplier_code or '').strip()
        if not supplier_code and self.supplier_product_code and self.supplier_product_code.product_code:
            supplier_code = self.supplier_product_code.product_code.strip()
        if not supplier_code and self.product_id.seller_ids:
            first_seller = self.product_id.seller_ids.filtered(lambda s: s.product_code)[:1]
            if first_seller and first_seller.product_code:
                supplier_code = first_seller.product_code.strip()

        return ProductLabelService.generate_label_image(
            self.product_id,
            supplier_product_code=supplier_code or None,
            nhap_date=self.nhap_date,
            dinh_luong=self.dinh_luong,
            custom_name=self.custom_name,
            format_id=self.format_id
        )

    def action_save_to_product(self):
        """Save generated label directly into product.template.label_image and reload product view"""
        self.ensure_one()
        label_image = self._generate_label_image_for_product()
        if label_image:
            self.product_id.sudo().write({'label_image': label_image})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã lưu tem sản phẩm'),
                'message': _('Tem sản phẩm đã được lưu và hiển thị trên sản phẩm "%s"!') % (self.product_id.name or ''),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    def action_save_format_settings(self):
        """Save current wizard format proxy fields to the format_id record"""
        self.ensure_one()
        if not self.format_id:
            raise UserError(_("Vui lòng chọn mẫu tem cần lưu!"))
        self.format_id.write({
            'name': self.format_name,
            'width_mm': self.format_width_mm,
            'height_mm': self.format_height_mm,
            'show_logo': self.format_show_logo,
            'logo_height_mm': self.format_logo_height_mm,
            'show_supplier_code': self.format_show_supplier_code,
            'supplier_code_display': self.format_supplier_code_display,
            'supplier_barcode_height_mm': self.format_supplier_barcode_height_mm,
            'supplier_font_size_pt': self.format_supplier_font_size_pt,
            'show_product_name': self.format_show_product_name,
            'product_name_font_size_pt': self.format_product_name_font_size_pt,
            'product_name_bold': self.format_product_name_bold,
            'product_name_align': self.format_product_name_align,
            'product_name_max_lines': self.format_product_name_max_lines,
            'show_separator_line': self.format_show_separator_line,
            'separator_color': self.format_separator_color,
            'separator_thickness_mm': self.format_separator_thickness_mm,
            'show_brand': self.format_show_brand,
            'brand_font_size_pt': self.format_brand_font_size_pt,
            'show_nhap_date': self.format_show_nhap_date,
            'nhap_date_font_size_pt': self.format_nhap_date_font_size_pt,
            'show_dinh_luong': self.format_show_dinh_luong,
            'dinh_luong_font_size_pt': self.format_dinh_luong_font_size_pt,
            'show_sku_barcode': self.format_show_sku_barcode,
            'sku_barcode_height_mm': self.format_sku_barcode_height_mm,
            'sku_font_size_pt': self.format_sku_font_size_pt,
            'border_style': self.format_border_style,
            'border_color': self.format_border_color,
            'border_width_mm': self.format_border_width_mm,
            'border_radius_mm': self.format_border_radius_mm,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã lưu mẫu tem'),
                'message': _("Cấu hình mẫu tem '%s' đã được lưu thành công!") % self.format_id.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_print_pdf(self):
        """Action invoked when user clicks 'In tem (Máy in nhiệt - Vector PDF)'"""
        self.ensure_one()
        if self.qty_to_print < 1:
            raise UserError(_("Số lượng tem in phải từ 1 trở lên!"))

        if not self.format_id:
            raise UserError(_("Vui lòng chọn Mẫu & Khổ in tem!"))

        # Consolidate supplier_code
        supplier_code = (self.supplier_code or '').strip()
        if not supplier_code and self.supplier_product_code and self.supplier_product_code.product_code:
            supplier_code = self.supplier_product_code.product_code.strip()
        if not supplier_code and self.product_id.seller_ids:
            first_seller = self.product_id.seller_ids.filtered(lambda s: s.product_code)[:1]
            if first_seller and first_seller.product_code:
                supplier_code = first_seller.product_code.strip()
        self.supplier_code = supplier_code

        # Synchronize paperformat for selected format
        paperformat = self.format_id.get_or_create_paperformat()
        report_action = self.env.ref('qba.action_report_product_label_vector')
        report_action.sudo().write({'paperformat_id': paperformat.id})

        # Always update product_id.label_image when printing!
        try:
            label_image = self._generate_label_image_for_product()
            if label_image:
                self.product_id.sudo().write({'label_image': label_image})
        except Exception:
            pass

        return report_action.report_action(self, config=False)

    def action_generate_label(self):
        """Retain action_generate_label for backwards compatibility, returning PDF report"""
        return self.action_print_pdf()

    def action_open_format_settings(self):
        """Open format form view in a modal dialog for customization before/during printing"""
        self.ensure_one()
        return {
            'name': _('Tùy biến Mẫu in tem QBA'),
            'type': 'ir.actions.act_window',
            'res_model': 'qba.product.label.format',
            'view_mode': 'form',
            'res_id': self.format_id.id if self.format_id else False,
            'target': 'new',
        }

    def action_create_new_format(self):
        """Open form view in modal to create a new format / paper size"""
        self.ensure_one()
        return {
            'name': _('Tạo Mẫu in tem mới'),
            'type': 'ir.actions.act_window',
            'res_model': 'qba.product.label.format',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f"Mẫu tem {self.format_width_mm:.0f}x{self.format_height_mm:.0f} mm",
                'default_width_mm': self.format_width_mm,
                'default_height_mm': self.format_height_mm,
            }
        }