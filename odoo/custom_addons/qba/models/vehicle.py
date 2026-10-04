from odoo import models, fields

class QbaVehicle(models.Model):
    _name = "qba.vehicle"
    _description = "Xe"

    name = fields.Char(string="Tên xe", required=True)
    brand = fields.Char(string="Hãng xe")  # HÃNG XE
    model_code = fields.Char(string="Model")  # MODEL
    category = fields.Char(string="Chủng loại")  # CHỦNG LOẠI
    engine_id = fields.Many2one('qba.engine', string='Động cơ')  # Động cơ
    gearbox_id = fields.Many2one('qba.gearbox', string='Hộp số')  # Hộp số
    year = fields.Char(string="Năm SX")  # NĂM SX
    certificate = fields.Char(string="Đặc chủng")  # ĐẶC CHỦNG
    axle = fields.Char(string="Cầu")  # Cầu
    note = fields.Char(string="Ghi chú")  # GHI CHÚ
    description = fields.Char(string="Mô tả thêm")  # MÔ TẢ THÊM
