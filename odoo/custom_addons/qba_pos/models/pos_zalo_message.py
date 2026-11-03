# -*- coding: utf-8 -*-
import json
import logging
import urllib.request
import urllib.error
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class PosZaloMessage(models.Model):
    _name = "pos.zalo.message"
    _description = "Nhat Ky Tin Nhan Zalo Bao Hanh POS"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Ma Tin Nhan",
        default=lambda self: _("New"),
        copy=False,
        readonly=True,
        tracking=True
    )
    pos_order_id = fields.Many2one(
        "pos.order",
        string="Don Hang POS",
        required=True,
        ondelete="cascade",
        tracking=True,
        index=True
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Khach Hang",
        required=True,
        tracking=True,
        index=True
    )
    phone = fields.Char(string="So Dien Thoai Zalo", required=True, tracking=True)
    customer_name = fields.Char(string="Ten Nguoi Nhan")
    message_content = fields.Text(string="Noi Dung Tin Nhan Bao Hanh", required=True)
    template_id = fields.Char(string="Ma Mau ZNS (Template ID)")
    state = fields.Selection([
        ("draft", "Du Thao"),
        ("sent", "Da Gui Thanh Cong"),
        ("simulated", "Mo Phong Thanh Cong"),
        ("failed", "Gui That Bai"),
    ], string="Trang Thai", default="draft", tracking=True, index=True)
    sent_date = fields.Datetime(string="Thoi Gian Gui")
    response_payload = fields.Text(string="Phan Hoi Tu Zalo API")
    error_message = fields.Text(string="Chi Tiet Loi")
    company_id = fields.Many2one(
        "res.company",
        string="Cong Ty",
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                seq = self.env["ir.sequence"].next_by_code("pos.zalo.message") or "ZALO"
                vals["name"] = seq
        return super().create(vals_list)

    def action_send_zalo(self):
        """Gui tin nhan bao hanh qua Zalo OpenAPI hoac che do mo phong."""
        ICP = self.env["ir.config_parameter"].sudo()
        mode = ICP.get_param("qba_pos.zalo_mode", "simulation")
        access_token = ICP.get_param("qba_pos.zalo_access_token", "").strip()

        for rec in self:
            cleaned_phone = (rec.phone or "").replace(" ", "").replace(".", "").replace("-", "").replace("+", "")
            if cleaned_phone.startswith("0"):
                cleaned_phone = "84" + cleaned_phone[1:]

            if mode == "production" and access_token:
                # Gui that qua Zalo OpenAPI
                url = "https://openapi.zalo.me/v3.0/oa/message/cs"
                payload = {
                    "recipient": {
                        "phone": cleaned_phone,
                    },
                    "message": {
                        "text": rec.message_content,
                    }
                }
                headers = {
                    "Content-Type": "application/json",
                    "access_token": access_token,
                }
                try:
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(url, data=data, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        res_body = response.read().decode("utf-8")
                        res_json = json.loads(res_body)
                        rec.write({
                            "response_payload": res_body,
                            "sent_date": fields.Datetime.now(),
                            "state": "sent" if res_json.get("error") == 0 else "failed",
                            "error_message": res_json.get("message") if res_json.get("error") != 0 else False,
                        })
                except Exception as e:
                    _logger.error("Loi khi gui tin nhan Zalo: %s", str(e))
                    rec.write({
                        "state": "failed",
                        "error_message": str(e),
                        "sent_date": fields.Datetime.now(),
                    })
            else:
                # Che do mo phong (Simulation): Luu nhat ky day du de thu nghiem
                rec.write({
                    "state": "simulated",
                    "sent_date": fields.Datetime.now(),
                    "response_payload": json.dumps({
                        "status": "simulation_success",
                        "recipient": cleaned_phone,
                        "mode": "Simulation (Cau hinh Zalo Access Token de gui that)",
                    }, indent=2, ensure_ascii=False),
                    "error_message": False,
                })
        return True

    def action_resend(self):
        """Gui lai tin nhan neu truoc do gap su co."""
        return self.action_send_zalo()

