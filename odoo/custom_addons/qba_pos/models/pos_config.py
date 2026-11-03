# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PosConfig(models.Model):
    _inherit = "pos.config"

    custom_manual_product_id = fields.Many2one(
        "product.product",
        string="San Pham Dung Cho Hang Nhap Tay",
        domain=[("sale_ok", "=", True)],
        default=lambda self: self.env["product.template"].get_or_create_custom_manual_product(),
        help="San pham dai dien de ghi nhan cac mat hang chua co tren he thong khi ban hang qua POS."
    )
    zalo_auto_send_warranty = fields.Boolean(
        string="Tu Dong Gui Tin Nhan Bao Hanh Qua Zalo",
        default=True,
        help="Tu dong tao va gui tin nhan thong tin bao hanh den Zalo cua khach hang sau khi thanh toan."
    )
    zalo_warranty_hotline = fields.Char(
        string="Hotline Bao Hanh / Ho Tro",
        default="0905.123.456",
        help="So dien thoai hotline lien he bao hanh gui kem trong tin nhan Zalo."
    )
    zalo_warranty_terms = fields.Text(
        string="Dieu Khoan Bao Hanh Mac Dinh",
        default="Bao hanh theo tieu chuan nha san xuat. Doi tra trong 7 ngay neu loi ky thuat va con nguyen tem.",
        help="Noi dung quy dinh bao hanh tom tat de dinh kem tin nhan Zalo."
    )
