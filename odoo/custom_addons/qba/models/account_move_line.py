# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    """Bổ sung các trường Deferred Revenue/Expense cho account.move.line trên Odoo Community 18.
    Tránh lỗi 'account.move.line object has no attribute deferred_start_date'
    khi xuất hóa đơn EDI (account_edi_ubl_cii) hoặc thanh toán xuất hóa đơn từ Point of Sale.
    """
    _inherit = "account.move.line"

    deferred_start_date = fields.Date(
        string="Ngày bắt đầu phân bổ",
        index=True,
        help="Ngày bắt đầu chu kỳ phân bổ chi phí/doanh thu trả trước (tương thích Odoo Community)"
    )
    deferred_end_date = fields.Date(
        string="Ngày kết thúc phân bổ",
        index=True,
        help="Ngày kết thúc chu kỳ phân bổ chi phí/doanh thu trả trước (tương thích Odoo Community)"
    )

