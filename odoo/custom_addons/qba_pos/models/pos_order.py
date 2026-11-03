# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    zalo_message_ids = fields.One2many(
        "pos.zalo.message",
        "pos_order_id",
        string="Lich Su Tin Nhan Zalo"
    )
    zalo_message_count = fields.Integer(
        string="So Tin Zalo",
        compute="_compute_zalo_message_count"
    )
    has_custom_manual_products = fields.Boolean(
        string="Co Hang Nhap Tay",
        compute="_compute_has_custom_manual_products",
        store=True,
        help="Danh dau don hang co chua it nhat 1 san pham nhap tay chua co ma trong kho."
    )

    @api.depends("zalo_message_ids")
    def _compute_zalo_message_count(self):
        for order in self:
            order.zalo_message_count = len(order.zalo_message_ids)

    @api.depends("lines.is_custom_manual_line", "lines.product_id.default_code")
    def _compute_has_custom_manual_products(self):
        for order in self:
            order.has_custom_manual_products = any(
                line.is_custom_manual_line or line.product_id.default_code == "SP_CHUA_CO_MA"
                for line in order.lines
            )

    @api.model
    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(order_id)
        if pos_order.exists():
            pos_order._record_custom_products_history()
            if pos_order.state in ("paid", "done"):
                pos_order._trigger_auto_zalo_warranty()
        return order_id

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        for order in self:
            order._record_custom_products_history()
            order._trigger_auto_zalo_warranty()
        return res

    def _record_custom_products_history(self):
        """Tu dong luu cac ten san pham nhap tay vao bang lich su de goi y autocomplete sau nay."""
        try:
            History = self.env["pos.custom.product.history"].sudo()
            for order in self:
                for line in order.lines:
                    if line.is_custom_manual_line or (line.product_id and line.product_id.default_code == "SP_CHUA_CO_MA"):
                        custom_name = (line.full_product_name or "").strip()
                        if custom_name and custom_name != line.product_id.name:
                            History.record_custom_name(
                                name=custom_name,
                                price=line.price_unit,
                                notes=line.customer_note or line.note or ""
                            )
        except Exception as e:
            _logger.error("Loi khi ghi nhan lich su san pham nhap tay: %s", str(e))

    def _trigger_auto_zalo_warranty(self):
        """Tu dong tao va gui tin nhan bao hanh qua Zalo neu khach hang co so dien thoai."""
        self.ensure_one()
        try:
            if not self.config_id.zalo_auto_send_warranty:
                return False

            partner = self.partner_id
            if not partner:
                return False

            phone = partner.mobile or partner.phone
            if not phone:
                return False

            # Tranh gui trung neu da co tin nhan thanh cong cho don nay
            existing = self.zalo_message_ids.filtered(lambda m: m.state in ("sent", "simulated"))
            if existing:
                return False

            message_content = self._build_warranty_message_text()
            zalo_msg = self.env["pos.zalo.message"].sudo().create({
                "pos_order_id": self.id,
                "partner_id": partner.id,
                "phone": phone,
                "customer_name": partner.name,
                "message_content": message_content,
            })
            zalo_msg.action_send_zalo()

            body = _("Da tao tin nhan bao hanh Zalo cho khach hang <b>%s</b> (%s) theo ma tin <b>%s</b>.") % (
                html_escape(partner.name or ""),
                html_escape(phone),
                html_escape(zalo_msg.name or "")
            )
            self.message_post(body=body)
            return True
        except Exception as e:
            _logger.error("Loi khi tu dong gui tin Zalo bao hanh cho don %s: %s", self.name, str(e))
            return False

    def _build_warranty_message_text(self):
        """Tao noi dung tin nhan xac nhan don hang va bao hanh gui khach."""
        self.ensure_one()
        partner_name = self.partner_id.name or "Quy khach"
        order_name = self.pos_reference or self.name
        order_date = fields.Date.today().strftime("%d/%m/%Y")
        hotline = self.config_id.zalo_warranty_hotline or "0905.123.456"
        terms = self.config_id.zalo_warranty_terms or "Bao hanh theo tieu chuan nha san xuat."

        lines_text = []
        for idx, line in enumerate(self.lines, 1):
            name = line.full_product_name or line.product_id.display_name
            qty = int(line.qty) if line.qty.is_integer() else line.qty
            subtotal = "{:,.0f}".format(line.price_subtotal_incl)
            lines_text.append(f"{idx}. {name} x {qty} ({subtotal} d)")

        items_str = "\n".join(lines_text)
        total_str = "{:,.0f} d".format(self.amount_total)

        msg = (
            f"PHU TUNG O TO Q.BA - XAC NHAN DON HANG & BAO HANH\n"
            f"Kinh chao: {partner_name}\n"
            f"Ma don: {order_name} - Ngay: {order_date}\n\n"
            f"DANH SACH PHU TUNG:\n"
            f"{items_str}\n"
            f"Tong thanh toan: {total_str}\n\n"
            f"CHINH SACH BAO HANH:\n"
            f"{terms}\n\n"
            f"Hotline ho tro / Bao hanh: {hotline}\n"
            f"Xin chan thanh cam on Quy khach!"
        )
        return msg

    def action_view_zalo_messages(self):
        self.ensure_one()
        return {
            "name": _("Tin Nhan Zalo Bao Hanh: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "pos.zalo.message",
            "view_mode": "list,form",
            "domain": [("pos_order_id", "=", self.id)],
            "context": {"default_pos_order_id": self.id, "default_partner_id": self.partner_id.id},
        }


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    is_custom_manual_line = fields.Boolean(
        string="La Hang Nhap Tay",
        default=False,
        help="Danh dau dong san pham nhap tay chua co ma trong danh muc."
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if "is_custom_manual_line" not in params:
            params.append("is_custom_manual_line")
        return params

    def _prepare_base_line_for_taxes_computation(self):
        """Dam bao ten san pham nhap tay duoc the hien tren hoa don va but toan cong no."""
        res = super()._prepare_base_line_for_taxes_computation()
        if self.full_product_name:
            res["name"] = self.full_product_name
        return res

