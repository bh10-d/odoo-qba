# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductLabelFormat(models.Model):
    _name = 'qba.product.label.format'
    _description = 'Mẫu cấu hình tem sản phẩm QBA'
    _order = 'is_default desc, name asc'

    name = fields.Char(string='Tên mẫu tem', required=True)
    code = fields.Char(string='Mã cấu hình')
    active = fields.Boolean(default=True, string='Đang dùng')
    is_default = fields.Boolean(string='Mẫu mặc định', default=False)
    description = fields.Text(string='Ghi chú / Mô tả')

    # 1. Kích thước & Lề (mm)
    width_mm = fields.Float(string='Chiều rộng (mm)', default=100.0, required=True)
    height_mm = fields.Float(string='Chiều cao (mm)', default=70.0, required=True)
    margin_top_mm = fields.Float(string='Lề trên (mm)', default=1.0)
    margin_bottom_mm = fields.Float(string='Lề dưới (mm)', default=1.0)
    margin_left_mm = fields.Float(string='Lề trái (mm)', default=1.0)
    margin_right_mm = fields.Float(string='Lề phải (mm)', default=1.0)
    orientation = fields.Selection([
        ('Landscape', 'Ngang (Landscape)'),
        ('Portrait', 'Dọc (Portrait)'),
    ], default='Landscape', string='Hướng khổ in', required=True)

    paperformat_id = fields.Many2one('report.paperformat', string='Khổ giấy hệ thống', readonly=True, ondelete='set null')

    # 2. Phần Đầu: Logo
    show_logo = fields.Boolean(string='Hiện Logo', default=True)
    logo_position = fields.Selection([
        ('left', 'Bên trái'),
        ('center', 'Ở giữa'),
        ('right', 'Bên phải'),
    ], default='left', string='Vị trí Logo')
    logo_height_mm = fields.Float(string='Chiều cao Logo (mm)', default=10.0)
    custom_logo = fields.Binary(string='Logo tùy chỉnh (PNG/SVG)', attachment=True, help="Nếu để trống sẽ sử dụng logo mặc định của QBA")

    # 3. Phần Đầu: Mã Nhà Cung Cấp
    show_supplier_code = fields.Boolean(string='Hiện Mã NCC', default=True)
    supplier_code_position = fields.Selection([
        ('right', 'Bên phải'),
        ('left', 'Bên trái'),
        ('center', 'Ở giữa'),
    ], default='right', string='Vị trí Mã NCC')
    supplier_code_display = fields.Selection([
        ('barcode_and_text', 'Cả mã vạch & chữ số'),
        ('text_only', 'Chỉ hiện chữ số'),
        ('barcode_only', 'Chỉ hiện mã vạch'),
    ], default='barcode_and_text', string='Kiểu hiển thị Mã NCC')
    supplier_barcode_height_mm = fields.Float(string='Chiều cao vạch NCC (mm)', default=7.5)
    supplier_font_size_pt = fields.Float(string='Cỡ chữ Mã NCC (pt)', default=7.5)

    # 4. Phần Thân: Tên Sản Phẩm
    show_product_name = fields.Boolean(string='Hiện tên sản phẩm', default=True)
    product_name_font_size_pt = fields.Float(string='Cỡ chữ tên SP (pt)', default=9.5)
    product_name_bold = fields.Boolean(string='In đậm tên SP', default=False)
    product_name_align = fields.Selection([
        ('left', 'Căn trái'),
        ('center', 'Căn giữa'),
        ('right', 'Căn phải'),
    ], default='left', string='Căn lề tên SP')
    product_name_max_lines = fields.Integer(string='Số dòng tên SP tối đa', default=3)

    # 5. Đường Ngăn Cách (Separator Line)
    show_separator_line = fields.Boolean(string='Hiện đường ngăn cách', default=True)
    separator_color = fields.Char(string='Màu đường kẻ (HEX)', default='#e43c24', help="Ví dụ #e43c24 hoặc #000000")
    separator_thickness_mm = fields.Float(string='Độ dày đường kẻ (mm)', default=0.6)

    # 6. Thông Tin Bổ Sung (Dưới đường kẻ)
    show_brand = fields.Boolean(string='Hiện Hãng / Thương hiệu', default=True)
    brand_font_size_pt = fields.Float(string='Cỡ chữ Hãng (pt)', default=8.0)

    show_nhap_date = fields.Boolean(string='Hiện Ngày nhập', default=True)
    nhap_date_font_size_pt = fields.Float(string='Cỡ chữ Ngày nhập (pt)', default=8.0)

    show_dinh_luong = fields.Boolean(string='Hiện Định lượng', default=True)
    dinh_luong_font_size_pt = fields.Float(string='Cỡ chữ Định lượng (pt)', default=8.0)

    # 7. Mã Vạch SKU Sản Phẩm
    show_sku_barcode = fields.Boolean(string='Hiện mã vạch SKU', default=True)
    sku_barcode_position = fields.Selection([
        ('bottom_center', 'Dưới cùng - Căn giữa'),
        ('bottom_left', 'Dưới cùng - Căn trái'),
        ('bottom_right', 'Dưới cùng - Căn phải'),
    ], default='bottom_center', string='Vị trí mã SKU')
    sku_barcode_height_mm = fields.Float(string='Chiều cao vạch SKU (mm)', default=9.0)
    sku_font_size_pt = fields.Float(string='Cỡ chữ SKU (pt)', default=8.0)

    # 8. Viền Khung Tem
    border_style = fields.Selection([
        ('rounded', 'Viền bo góc'),
        ('square', 'Viền vuông'),
        ('none', 'Không có viền'),
    ], default='rounded', string='Kiểu viền tem')
    border_color = fields.Char(string='Màu viền (HEX)', default='#e43c24')
    border_width_mm = fields.Float(string='Độ dày viền (mm)', default=0.6)
    border_radius_mm = fields.Float(string='Bán kính bo góc (mm)', default=2.5)

    # 9. Tùy biến CSS nâng cao (dành cho Admin kỹ thuật)
    custom_css = fields.Text(string='CSS tùy biến bổ sung', help="Admin có thể thêm CSS đặc thù cho máy in hoặc layout")

    @api.constrains('width_mm', 'height_mm')
    def _check_dimensions(self):
        for rec in self:
            if rec.width_mm <= 0 or rec.height_mm <= 0:
                raise ValidationError(_("Chiều rộng và chiều cao của tem phải lớn hơn 0 mm!"))

    @api.constrains('is_default')
    def _check_is_default(self):
        for rec in self:
            if rec.is_default:
                other_defaults = self.search([('id', '!=', rec.id), ('is_default', '=', True)])
                if other_defaults:
                    other_defaults.write({'is_default': False})

    def action_set_as_default(self):
        self.ensure_one()
        self.is_default = True

    def get_or_create_paperformat(self):
        """
        Create or synchronize an ir.actions.report paperformat matching this label format.
        """
        self.ensure_one()
        fmt = self.sudo()
        paperformat_obj = self.env['report.paperformat'].sudo()
        pf_name = f"Tem QBA - {fmt.name} ({fmt.width_mm:.0f}x{fmt.height_mm:.0f}mm)"

        vals = {
            'name': pf_name,
            'format': 'custom',
            'page_width': fmt.width_mm,
            'page_height': fmt.height_mm,
            'margin_top': 0.0,
            'margin_bottom': 0.0,
            'margin_left': 0.0,
            'margin_right': 0.0,
            'orientation': 'Portrait',
            'header_line': False,
            'header_spacing': 0,
            'disable_shrinking': True,
            'dpi': 96,
        }

        if fmt.paperformat_id:
            fmt.paperformat_id.write(vals)
            return fmt.paperformat_id

        # Search existing by name
        existing = paperformat_obj.search([('name', '=', pf_name)], limit=1)
        if existing:
            existing.write(vals)
            fmt.paperformat_id = existing
            return existing

        created = paperformat_obj.create(vals)
        fmt.paperformat_id = created
        return created

