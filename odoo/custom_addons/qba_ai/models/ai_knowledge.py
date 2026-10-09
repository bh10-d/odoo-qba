# -*- coding: utf-8 -*-
from odoo import models, fields, api

class QbaAiKnowledge(models.Model):
    _name = "qba.ai.knowledge"
    _description = "Thư Viện Kiến Thức & Hướng Dẫn Đo Phụ Tùng"
    _order = "sequence, id desc"

    name = fields.Char(string="Tiêu đề bài hướng dẫn", required=True)
    category = fields.Selection([
        ('measurement', 'Hướng dẫn đo đạc thông số'),
        ('oe_lookup', 'Tra cứu mã OE / Mã tương đương'),
        ('product_spec', 'Giải thích thông số kỹ thuật'),
        ('other', 'Kiến thức khác')
    ], string="Phân loại", default='measurement', required=True)
    
    content = fields.Html(string="Nội dung chi tiết hướng dẫn", required=True)
    summary = fields.Text(string="Tóm tắt ngắn (Dành cho AI context)")
    keywords = fields.Char(string="Từ khóa tìm kiếm (phân cách bằng dấu phẩy)", help="VD: đường kính đĩa phanh, lỗ ốc, moay ơ, vios")
    product_category_id = fields.Many2one('product.category', string="Danh mục sản phẩm áp dụng")
    active = fields.Boolean(string="Kích hoạt", default=True)
    sequence = fields.Integer(string="Thứ tự ưu tiên", default=10)

    def name_get(self):
        result = []
        for rec in self:
            name = f"[{dict(self._fields['category'].selection).get(rec.category)}] {rec.name}"
            result.append((rec.id, name))
        return result
