# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    discount_amount = fields.Monetary(
        string="CK",
        currency_field='currency_id',
        copy=True,
        help="Số tiền chiết khấu trực tiếp bằng số tiền cụ thể."
    )

    @api.constrains('discount_amount', 'discount', 'price_unit', 'product_qty')
    def _check_discount_validity(self):
        """Kiểm tra an toàn tài chính: Chiết khấu không âm và không vượt quá tổng tiền hàng."""
        for line in self:
            if line.discount_amount < 0:
                raise ValidationError(_("Tiền chiết khấu (CK) không thể là số âm."))
            if line.discount < 0 or line.discount > 100:
                raise ValidationError(_("Tỷ lệ chiết khấu (% CK) phải nằm trong khoảng từ 0% đến 100%."))
            total = abs(line.price_unit * line.product_qty)
            if total and line.discount_amount > total:
                raise ValidationError(_(
                    "Tiền chiết khấu (%(discount)s) không thể lớn hơn tổng tiền hàng của dòng (%(total)s).",
                    discount=line.discount_amount,
                    total=total,
                ))

    @api.onchange('discount_amount')
    def _onchange_discount_amount(self):
        for line in self:
            total_before_discount = abs(line.price_unit * line.product_qty)
            if total_before_discount:
                line.discount = (line.discount_amount / total_before_discount) * 100.0
            else:
                line.discount = 0.0

    @api.onchange('discount', 'price_unit', 'product_qty')
    def _onchange_discount_or_price(self):
        for line in self:
            total_before_discount = abs(line.price_unit * line.product_qty)
            expected_discount_amount = total_before_discount * (line.discount / 100.0)
            if abs((line.discount_amount or 0.0) - expected_discount_amount) > 0.01:
                line.discount_amount = expected_discount_amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            qty = vals.get('product_qty', 0.0)
            price = vals.get('price_unit', 0.0)
            total = abs(qty * price)
            if 'discount_amount' in vals and 'discount' not in vals:
                vals['discount'] = (vals['discount_amount'] / total * 100.0) if total else 0.0
            elif 'discount' in vals and 'discount_amount' not in vals:
                vals['discount_amount'] = total * (vals['discount'] / 100.0)
        return super().create(vals_list)

    def write(self, vals):
        # Nếu cập nhật nhiều dòng cùng lúc với giá hoặc chiết khấu, xử lý từng dòng để tránh ghi đè sai giá trị
        if len(self) > 1 and any(f in vals for f in ('discount_amount', 'discount', 'product_qty', 'price_unit')):
            for line in self:
                line.write(dict(vals))
            return True

        if 'discount_amount' in vals and 'discount' not in vals:
            qty = vals.get('product_qty', self.product_qty)
            price = vals.get('price_unit', self.price_unit)
            total = abs(qty * price)
            vals['discount'] = (vals['discount_amount'] / total * 100.0) if total else 0.0
        elif 'discount' in vals and 'discount_amount' not in vals:
            qty = vals.get('product_qty', self.product_qty)
            price = vals.get('price_unit', self.price_unit)
            total = abs(qty * price)
            vals['discount_amount'] = total * (vals['discount'] / 100.0)
        elif ('product_qty' in vals or 'price_unit' in vals) and 'discount_amount' not in vals and 'discount' not in vals:
            if self.discount:
                qty = vals.get('product_qty', self.product_qty)
                price = vals.get('price_unit', self.price_unit)
                total = abs(qty * price)
                vals['discount_amount'] = total * (self.discount / 100.0)

        return super().write(vals)

    @api.depends('discount_amount')
    def _compute_amount(self):
        super()._compute_amount()

    @api.depends('discount', 'price_unit', 'discount_amount', 'product_qty')
    def _compute_price_unit_discounted(self):
        for line in self:
            qty = abs(line.product_qty)
            if line.discount_amount and qty:
                line.price_unit_discounted = max(0.0, (line.price_unit * qty - line.discount_amount) / qty)
            else:
                super(PurchaseOrderLine, line)._compute_price_unit_discounted()

    def _prepare_base_line_for_taxes_computation(self):
        base_line = super()._prepare_base_line_for_taxes_computation()
        qty = abs(self.product_qty)
        if self.discount_amount and qty:
            price_unit_after_discount = max(0.0, (self.price_unit * qty - self.discount_amount) / qty)
            base_line['price_unit'] = price_unit_after_discount
            base_line['discount'] = 0.0
        return base_line

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move=move)
        qty = abs(self.product_qty)
        if self.discount_amount and qty:
            price_unit_after_discount = max(0.0, (self.price_unit * qty - self.discount_amount) / qty)
            aml_currency = move and move.currency_id or self.currency_id
            date = move and move.date or fields.Date.today()
            res['price_unit'] = self.currency_id._convert(
                price_unit_after_discount,
                aml_currency,
                self.company_id,
                date,
                round=False
            )
            res['discount'] = 0.0
        return res

    def _get_stock_move_price_unit(self):
        """Đảm bảo đơn giá trên dịch chuyển nhập kho (stock.move) tính theo đơn giá đã trừ chiết khấu,
        giúp định giá tồn kho (Inventory Valuation) khớp 100% với giá trị thanh toán thực tế."""
        price_unit = super()._get_stock_move_price_unit()
        if (self.discount_amount or self.discount) and self.price_unit and self.product_qty:
            ratio = self.price_unit_discounted / self.price_unit
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            return float_round(price_unit * ratio, precision_digits=price_unit_prec)
        return price_unit
