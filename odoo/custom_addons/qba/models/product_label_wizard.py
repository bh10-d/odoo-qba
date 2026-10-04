from odoo import models, fields, api, _
from odoo.exceptions import UserError
from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
from reportlab.graphics.barcode import createBarcodeDrawing


class ProductLabelService:
    """Service class for generating product labels"""
    
    @staticmethod
    def get_unicode_font(size=18):
        """Get font that supports Vietnamese Unicode"""
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            'C:/Windows/Fonts/arial.ttf',
            '/System/Library/Fonts/Arial.ttf',
        ]
        for path in font_paths:
            try:
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
            except:
                continue
        return ImageFont.load_default()

    @staticmethod
    def generate_barcode_image(value, symbology='Code128', width=200, height=40):
        """Generate barcode image from text"""
        try:
            drawing = createBarcodeDrawing(
                symbology,
                value=str(value),
                format='png',
                width=width,
                height=height,
                humanReadable=False,
                barHeight=height
            )
            return Image.open(BytesIO(drawing.asString('png')))
        except Exception as e:
            print(f"Error creating barcode: {e}")
            return None

    @staticmethod
    def generate_label_image(product, supplier_product_code=None, nhap_date=None, dinh_luong=None, custom_name=None):
        """Generate product label image with new design"""
        W, H = 1000, 700
        P = 40  # padding
        label = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(label)
        
        # Fonts
        font_qba = ProductLabelService.get_unicode_font(40)
        font = ProductLabelService.get_unicode_font(28)
        font_small = ProductLabelService.get_unicode_font(24)

        # Viền bo góc với màu mới
        border_radius = 32
        border_color = "#e43c24"  # Màu đỏ cam
        border_width = 6
        mask = Image.new("L", (W, H), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (W-1, H-1)], radius=border_radius, fill=255)
        border = Image.new("RGBA", (W, H), (0,0,0,0))
        border_draw = ImageDraw.Draw(border)
        border_draw.rounded_rectangle([(border_width//2, border_width//2), (W-1-border_width//2, H-1-border_width//2)], radius=border_radius, outline=border_color, width=border_width)

        # --- PHẦN ĐẦU ---
        # Dòng 1: Logo (trái) và barcode supplier_product_code (phải)
        logo_x = P
        logo_y = P
        logo_w, logo_h = 0, 0
        
        # Load logo từ thư mục addon
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'src', 'img', 'logo.png')
        if os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                logo_img.thumbnail((300, 120), Image.Resampling.LANCZOS)
                label.paste(logo_img, (logo_x, logo_y), logo_img)
                logo_w, logo_h = logo_img.size
            except Exception as e:
                print(f"Error loading logo: {e}")
                # Draw logo placeholder
                logo_w, logo_h = 200, 80
                draw.rectangle([logo_x, logo_y, logo_x + logo_w, logo_y + logo_h], outline='black', width=2)
                draw.text((logo_x + 10, logo_y + 30), 'Logo', fill='black', font=font)
        else:
            # Draw logo placeholder
            logo_w, logo_h = 200, 80
            draw.rectangle([logo_x, logo_y, logo_x + logo_w, logo_y + logo_h], outline='black', width=2)
            draw.text((logo_x + 10, logo_y + 30), 'Logo', fill='black', font=font)

        # Provider SKU barcode (phải) - sử dụng supplier_product_code
        barcode_img = None
        barcode_w, barcode_h = 0, 0
        if supplier_product_code:
            barcode_img = ProductLabelService.generate_barcode_image(supplier_product_code, width=520, height=96)
            if barcode_img:
                barcode_w, barcode_h = barcode_img.size
        
        # Barcode căn phải, không đè lên logo
        barcode_x = W - P - barcode_w if barcode_w else W - P - 200
        barcode_y = logo_y
        if barcode_img:
            label.paste(barcode_img, (barcode_x, barcode_y))
            # Text mã barcode căn giữa dưới barcode
            text_w = font_small.getbbox(supplier_product_code)[2] - font_small.getbbox(supplier_product_code)[0]
            text_x = barcode_x + (barcode_w - text_w) // 2
            draw.text((text_x, barcode_y + barcode_h + 2), supplier_product_code, font=font_small, fill="black")

        # Dòng 2: Tên sản phẩm (chỉ 1 dòng, tự động co chữ)
        product_name = custom_name or product.name or ''
        font_product = ProductLabelService.get_unicode_font(40)
        max_text_width = W - 2 * P
        max_height = 260  # giới hạn chiều cao cho block tên sản phẩm

        # Ước lượng chiều cao mỗi dòng
        line_height = font_product.getbbox("A")[3] - font_product.getbbox("A")[1] + 20

        # Wrap text theo chiều rộng với logic cải tiến
        words = product_name.split()
        wrapped_lines = []
        current_line = []
        
        for word in words:
            # Test thêm từ này vào dòng hiện tại
            test_line = ' '.join(current_line + [word])
            try:
                line_width = font_product.getlength(test_line)
            except:
                # Fallback nếu font không hỗ trợ getlength
                line_width = len(test_line) * 15  # Approximate width
                
            if line_width <= max_text_width:
                # Từ này vừa, thêm vào dòng hiện tại
                current_line.append(word)
            else:
                # Từ này không vừa
                if current_line:
                    # Lưu dòng hiện tại và bắt đầu dòng mới
                    wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Từ đơn lẻ quá dài, bắt buộc xuống dòng
                    wrapped_lines.append(word)
                    current_line = []
        
        # Thêm dòng cuối cùng
        if current_line:
            wrapped_lines.append(' '.join(current_line))

        # Lọc số dòng sao cho không vượt quá max_height
        final_lines = []
        total_height = 0
        for line in wrapped_lines:
            if total_height + line_height > max_height:
                break
            final_lines.append(line)
            total_height += line_height

        # Vị trí bắt đầu vẽ
        product_y = max(logo_y + logo_h, barcode_y + barcode_h + 30) + 40

        # Vẽ các dòng
        for i, line in enumerate(final_lines):
            draw.text((P, product_y + i * line_height), line, font=font_product, fill="black")

        # Luôn đặt sep_y cố định sau tên sản phẩm 130px
        product_y += 260
        sep_y = product_y - 20  # Đẩy line break lên cao hơn 20px

        sep_height = 6
        sep_color = "#e43c24"  # Đổi màu line giống border

        # Vẽ đường thẳng không tràn quá border
        line_padding = border_width + 5  # Giảm padding để line dài hơn
        draw.rectangle([(line_padding, sep_y), (W - line_padding, sep_y+sep_height)], fill=sep_color)

        # --- PHẦN DƯỚI ---
        # Dòng 1: Ngày nhập (phải)
        below_y = sep_y + sep_height + 20
        nhap_text = f"{nhap_date.strftime('%d/%m/%Y') if nhap_date else ''}"  # Bỏ chữ "NGÀY NHẬP:", chỉ giữ ngày
        nhap_w = font.getbbox(nhap_text)[2] - font.getbbox(nhap_text)[0]
        draw.text((W - P - nhap_w, below_y), nhap_text, font=font, fill="black")

        # Dòng 2: Định lượng (dưới ngày nhập, cùng bên phải)
        dinh_luong_text = f"ĐL: {dinh_luong or ''}"  # Đổi thành "ĐL:"
        dinh_luong_w = font.getbbox(dinh_luong_text)[2] - font.getbbox(dinh_luong_text)[0]
        dinh_luong_y = below_y + font.getbbox(nhap_text)[3] - font.getbbox(nhap_text)[1] + 10  # Dưới ngày nhập
        draw.text((W - P - dinh_luong_w, dinh_luong_y), dinh_luong_text, font=font, fill="black")

        # Dòng 3: barcode product_sku ở giữa (không label, sát hơn với dòng trên)
        code_img = None
        code_w, code_h = 0, 0
        if product.default_code:
            code_img = ProductLabelService.generate_barcode_image(product.default_code, width=520, height=96)
            if code_img:
                code_w, code_h = code_img.size
        code_x = (W - code_w) // 2 if code_w else W//2
        code_y = dinh_luong_y + font.getbbox(dinh_luong_text)[3] - font.getbbox(dinh_luong_text)[1] + 30  # Giảm từ 50 xuống 30 để đưa lên cao hơn
        if code_img:
            label.paste(code_img, (code_x, code_y))
            # Text mã ngay dưới barcode, giảm khoảng cách
            text_w = font_small.getbbox(product.default_code)[2] - font_small.getbbox(product.default_code)[0]
            text_x = code_x + (code_w - text_w) // 2
            draw.text((text_x, code_y + code_h + 2), product.default_code, font=font_small, fill="black")

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
    supplier_product_code = fields.Many2one('product.supplierinfo', string='Mã nhà cung cấp', 
                                          domain="[('product_tmpl_id', '=', product_id)]")
    custom_name = fields.Char(string='Tên sản phẩm')  # Bỏ required
    nhap_date = fields.Date(string='Ngày nhập')  # Bỏ required
    dinh_luong = fields.Char(string='Định lượng')  # Bỏ required

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.custom_name = self.product_id.name
            self.supplier_product_code = False  # Reset supplier selection

    def action_generate_label(self):
        self.ensure_one()
        # Get supplier product code
        supplier_code = self.supplier_product_code.product_code if self.supplier_product_code else None
        
        # Generate label using service
        label_image = ProductLabelService.generate_label_image(
            self.product_id,
            supplier_product_code=supplier_code,
            nhap_date=self.nhap_date,
            dinh_luong=self.dinh_luong,
            custom_name=self.custom_name
        )
        # Update product label image
        self.product_id.label_image = label_image
        return {'type': 'ir.actions.act_window_close'} 