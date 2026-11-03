# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    zalo_mode = fields.Selection([
        ("simulation", "Che Do Mo Phong (Ghi Nhan & Kiem Thu - Khong Can API Key)"),
        ("production", "Che Do Chinh Thuc (Ket Noi Zalo OpenAPI / ZNS)"),
    ], string="Che Do Zalo", default="simulation", config_parameter="qba_pos.zalo_mode")

    zalo_oa_id = fields.Char(
        string="Zalo Official Account (OA) ID",
        config_parameter="qba_pos.zalo_oa_id"
    )
    zalo_app_id = fields.Char(
        string="Zalo App ID",
        config_parameter="qba_pos.zalo_app_id"
    )
    zalo_secret_key = fields.Char(
        string="Zalo Secret Key",
        config_parameter="qba_pos.zalo_secret_key"
    )
    zalo_access_token = fields.Char(
        string="Zalo Access Token",
        config_parameter="qba_pos.zalo_access_token"
    )
    zalo_refresh_token = fields.Char(
        string="Zalo Refresh Token",
        config_parameter="qba_pos.zalo_refresh_token"
    )
    zalo_template_id = fields.Char(
        string="ZNS Template ID",
        config_parameter="qba_pos.zalo_template_id"
    )

    def action_enable_all_products_for_pos(self):
        """Action nhanh cho phep quan tri vien bam kich hoat toan bo san pham vao POS ngay trong Settings."""
        return self.env["product.template"].action_enable_all_products_in_pos()

    def action_sync_all_pos_categories(self):
        """Action dong bo nhanh toan bo danh muc san pham sang danh muc POS."""
        self.env["product.template"].action_sync_pos_categories()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Dong Bo Danh Muc POS"),
                "message": _("Da dong bo toan bo danh muc phu tung sang POS Category thanh cong."),
                "type": "success",
                "sticky": False,
            }
        }
