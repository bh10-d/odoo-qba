# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont
import os
from reportlab.graphics.barcode.code128 import Code128


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
    def generate_label_image(cls, product, supplier_product_code=None, nhap_date=None, dinh_luong=None, custom_name=None):
        """Generate product label image with high-contrast, perfectly aligned layout"""
        W, H = 1000, 700
        P = 40  # padding
        label = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(label)

        # Fonts
        font_product = cls.get_unicode_font(38)
        font = cls.get_unicode_font(28)
        font_small = cls.get_unicode_font(24)

        # Viền bo góc màu đỏ cam QBA
        border_radius = 32
        border_color = "#e43c24"
        border_width = 6
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
        if os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                logo_img.thumbnail((280, 110), Image.Resampling.LANCZOS)
                label.paste(logo_img, (logo_x, logo_y), logo_img)
                logo_w, logo_h = logo_img.size
            except Exception:
                logo_w, logo_h = 200, 80
                draw.rectangle([logo_x, logo_y, logo_x + logo_w, logo_y + logo_h], outline='black', width=2)
                draw.text((logo_x + 10, logo_y + 25), 'QBA', fill='black', font=font_product)
        else:
            logo_w, logo_h = 200, 80
            draw.rectangle([logo_x, logo_y, logo_x + logo_w, logo_y + logo_h], outline='black', width=2)
            draw.text((logo_x + 10, logo_y + 25), 'QBA', fill='black', font=font_product)

        # Barcode & mã nhà cung cấp (phải)
        supplier_code_str = (supplier_product_code or '').strip()
        # Fallback to seller_ids if not explicitly passed
        if not supplier_code_str and product.seller_ids:
            first_seller = product.seller_ids.filtered(lambda s: s.product_code)[:1]
            if first_seller:
                supplier_code_str = (first_seller.product_code or '').strip()

        barcode_h = 75
        barcode_w = 420
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
        words = product_name.split()
        wrapped_lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            try:
                line_w = font_product.getlength(test_line)
            except Exception:
                line_w = len(test_line) * 16
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

        line_bbox = font_product.getbbox("Ay")
        line_height = (line_bbox[3] - line_bbox[1]) + 16

        top_elements_bottom = max(logo_y + logo_h, barcode_y + (barcode_h + 30 if supplier_code_str else 0))
        product_y = top_elements_bottom + 30

        final_lines = wrapped_lines[:3]
        for i, line in enumerate(final_lines):
            draw.text((P, product_y + i * line_height), line, font=font_product, fill="black")

        text_end_y = product_y + len(final_lines) * line_height

        # --- 3. ĐƯỜNG PHÂN CÁCH (Separator Line) ---
        sep_y = max(text_end_y + 25, 430)
        sep_y = min(sep_y, 480)
        sep_height = 6
        sep_color = "#e43c24"
        line_padding = border_width + 5
        draw.rectangle([(line_padding, sep_y), (W - line_padding, sep_y + sep_height)], fill=sep_color)

        # --- 4. PHẦN DƯỚI (Bottom Section) ---
        # Ngày nhập & Định lượng (Góc phải dưới line)
        meta_y = sep_y + sep_height + 15
        final_nhap_date = nhap_date or product.last_purchase_date
        if final_nhap_date:
            nhap_text = final_nhap_date.strftime('%d/%m/%Y')
            nhap_bbox = font.getbbox(nhap_text)
            nhap_w = nhap_bbox[2] - nhap_bbox[0]
            draw.text((W - P - nhap_w, meta_y), nhap_text, font=font, fill="black")
            meta_y += (nhap_bbox[3] - nhap_bbox[1]) + 8

        final_dinh_luong = dinh_luong or (f"1 {product.uom_id.name}".strip() if product.uom_id else "")
        if final_dinh_luong:
            dl_text = f"ĐL: {final_dinh_luong}"
            dl_bbox = font.getbbox(dl_text)
            dl_w = dl_bbox[2] - dl_bbox[0]
            draw.text((W - P - dl_w, meta_y), dl_text, font=font, fill="black")

        # Hãng / Thương hiệu (Góc trái dưới line)
        if product.brand_id:
            brand_text = f"Hãng: {product.brand_id.name}"
            draw.text((P, sep_y + sep_height + 15), brand_text, font=font, fill="black")

        # Mã vạch SKU sản phẩm (Căn giữa phía dưới)
        sku_val = (product.default_code or '').strip()
        if sku_val:
            code_w = 480
            code_h = 80
            code_img = cls.generate_barcode_image(sku_val, width=code_w, height=code_h)
            bottom_area_start = sep_y + sep_height
            bottom_area_end = H - border_width - 15
            total_code_h = code_h + 30
            code_y = bottom_area_start + (bottom_area_end - bottom_area_start - total_code_h) // 2

            code_x = (W - code_w) // 2
            if code_img:
                label.paste(code_img, (code_x, code_y), code_img)
                t_bbox = font_small.getbbox(sku_val)
                t_w = t_bbox[2] - t_bbox[0]
                t_x = code_x + (code_w - t_w) // 2
                draw.text((t_x, code_y + code_h + 4), sku_val, font=font_small, fill="black")
            else:
                # Nếu không tạo được vạch, vẫn vẽ mã SKU to rõ ràng ở giữa
                t_bbox = font_product.getbbox(sku_val)
                t_w = t_bbox[2] - t_bbox[0]
                t_x = (W - t_w) // 2
                draw.text((t_x, code_y + 20), sku_val, font=font_product, fill="black")

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

    def action_generate_label(self):
        self.ensure_one()
        # Lấy supplier_code ưu tiên từ ô nhập liệu hoặc dropdown supplierinfo
        supplier_code = (self.supplier_code or '').strip()
        if not supplier_code and self.supplier_product_code and self.supplier_product_code.product_code:
            supplier_code = self.supplier_product_code.product_code.strip()
        if not supplier_code and self.product_id.seller_ids:
            first_seller = self.product_id.seller_ids.filtered(lambda s: s.product_code)[:1]
            if first_seller and first_seller.product_code:
                supplier_code = first_seller.product_code.strip()

        # Generate label using service
        label_image = ProductLabelService.generate_label_image(
            self.product_id,
            supplier_product_code=supplier_code or None,
            nhap_date=self.nhap_date,
            dinh_luong=self.dinh_luong,
            custom_name=self.custom_name
        )
        # Update product label image
        self.product_id.label_image = label_image
        return {'type': 'ir.actions.act_window_close'}