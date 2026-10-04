from odoo import models, fields

class QbaEngine(models.Model):
    _name = "qba.engine"
    _description = "Động cơ xe"

    brand = fields.Char(string="Nhãn hiệu")  # Nhãn hiệu (lưu trữ)
    name = fields.Char(string="Động cơ")  # Tên động cơ (thể hiện)
    capacity = fields.Char(string="Dung tích xy lanh")  # Dung tích xy lanh
    horsepower = fields.Char(string="Mã lực HP")  # Mã lực HP
    torque = fields.Char(string="Lực kéo")  # Lực kéo
    emission_standard = fields.Char(string="Tiêu chuẩn khí thải")  # Tiêu chuẩn khí thải
    category = fields.Char(string="Chủng loại")  # Chủng loại (xe khách, xe tải...)
    vehicle_models = fields.Char(string="Các mẫu xe sử dụng")  # Các mẫu xe sử dụng
    note = fields.Char(string="Ghi chú thêm")  # Ghi chú thêm
