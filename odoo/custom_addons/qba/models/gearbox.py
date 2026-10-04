from odoo import models, fields

class QbaGearbox(models.Model):
    _name = "qba.gearbox"
    _description = "Hộp số xe"

    name = fields.Char(string="Mã hộp số")  # Mã hộp số
    brand = fields.Char(string="Nhãn hiệu")  # Nhãn hiệu
    ratio = fields.Char(string="Ratio")  # Ratio
    category = fields.Char(string="Chủng loại")  # Chủng loại (12 số tiến + 2 số lùi...)
    note = fields.Char(string="Ghi chú")  # Ghi chú (mô tả đặc tính)
    vehicle_models = fields.Char(string="Loại xe sử dụng")  # Loại xe sử dụng (HOWO, Volvo...)
