# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Tu dong thiet lap may POS, phuong thuc thanh toan va kich hoat POS cho toan bo san pham."""
    # 1. Kich hoat diem ban hang cho toan bo san pham hop le
    ProductTemplate = env["product.template"]
    products = ProductTemplate.search([
        ("sale_ok", "=", True),
        ("available_in_pos", "=", False),
    ])
    if products:
        products.write({"available_in_pos": True})

    # 2. Lay hoac tao san pham nhap tay SP_CHUA_CO_MA
    custom_product = ProductTemplate.get_or_create_custom_manual_product()

    # 3. Thiet lap cac phuong thuc thanh toan POS
    PosPaymentMethod = env["pos.payment.method"]
    AccountJournal = env["account.journal"]

    cash_journal = AccountJournal.search([("type", "=", "cash")], limit=1)
    bank_journal = AccountJournal.search([("type", "=", "bank")], limit=1)

    cash_pm = PosPaymentMethod.search([("name", "=", "Tien Mat")], limit=1)
    if not cash_pm and cash_journal:
        cash_pm = PosPaymentMethod.create({
            "name": "Tien Mat",
            "journal_id": cash_journal.id,
            "receivable_account_id": cash_journal.default_account_id.id if cash_journal.default_account_id else False,
        })

    bank_pm = PosPaymentMethod.search([("name", "=", "Chuyen Khoan Ngan Hang")], limit=1)
    if not bank_pm and bank_journal:
        bank_pm = PosPaymentMethod.create({
            "name": "Chuyen Khoan Ngan Hang",
            "journal_id": bank_journal.id,
            "receivable_account_id": bank_journal.default_account_id.id if bank_journal.default_account_id else False,
        })

    debt_pm = PosPaymentMethod.search([("name", "=", "Cong No Khach Hang (Ghi So)")], limit=1)
    if not debt_pm:
        debt_pm = PosPaymentMethod.create({
            "name": "Cong No Khach Hang (Ghi So)",
            "split_transactions": True,
        })

    payment_method_ids = [pm.id for pm in [cash_pm, bank_pm, debt_pm] if pm]

    # 4. Thiet lap May POS Ban Le Q.BA
    PosConfig = env["pos.config"]
    existing_config = PosConfig.search([("name", "=", "POS Ban Le Q.BA")], limit=1)
    if not existing_config:
        stock_picking_type = env["stock.picking.type"].search([("code", "=", "outgoing")], limit=1)
        config_vals = {
            "name": "POS Ban Le Q.BA",
            "picking_type_id": stock_picking_type.id if stock_picking_type else False,
            "payment_method_ids": [(6, 0, payment_method_ids)],
            "custom_manual_product_id": custom_product.id if custom_product else False,
            "zalo_auto_send_warranty": True,
            "zalo_warranty_hotline": "0905.123.456",
            "zalo_warranty_terms": "Bao hanh theo tieu chuan nha san xuat. Doi tra trong 7 ngay neu con nguyen tem.",
            "is_header_or_footer": True,
            "receipt_header": "PHU TUNG O TO Q.BA\nChuyen phu tung xe tai, xe ben, dau keo HOWO, SHACMAN, CHENGLONG\nHotline / Zalo: 0905.123.456",
            "receipt_footer": "Cam on Quy khach & Hen gap lai!\nQuy khach vui long kiem tra ky phu tung truoc khi roi cua hang.\nThong tin bao hanh da duoc gui qua Zalo cua Quy khach.",
            "iface_print_auto": True,
        }
        PosConfig.create(config_vals)
