# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api, _
from .api_utils import get_odoo_api_headers

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_public_url = fields.Char(
        string="Địa chỉ Website (Public Frontend)",
        config_parameter="qba.website_public_url",
        default="http://localhost:3000",
        help="Địa chỉ trang web công khai mở trên trình duyệt (vd: https://phutungqba.io.vn/)"
    )
    website_api_url = fields.Char(
        string="Địa chỉ Backend API",
        config_parameter="qba.website_api_url",
        default="http://host.docker.internal:5000/api/v1",
        help="Địa chỉ API Web SEO (vd: https://be.phutungqba.io.vn/api/v1)"
    )
    website_api_secret = fields.Char(
        string="Khóa bí mật HMAC (Shared Secret)",
        config_parameter="qba.website_api_secret",
        default="qba_odoo_enterprise_m2m_hmac_secret_2026_super_secure",
        help="Khóa bí mật dùng để sinh chữ ký điện tử HMAC-SHA256 khi gọi API sang Backend Express (không bao giờ truyền trực tiếp qua mạng)."
    )

    def action_test_website_api_connection(self):
        """Kiểm tra kết nối tới Backend API"""
        self.ensure_one()
        api_url = (self.website_api_url or 'http://host.docker.internal:5000/api/v1').strip().rstrip('/')
        if 'localhost:5000' in api_url or '127.0.0.1:5000' in api_url:
            api_url = api_url.replace('localhost:5000', 'host.docker.internal:5000').replace('127.0.0.1:5000', 'host.docker.internal:5000')

        test_url = f"{api_url}/products/verify-auth"
        try:
            headers = get_odoo_api_headers(self.env)
            resp = requests.get(test_url, headers=headers, timeout=3.5)
            if resp.status_code == 200:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Kết nối & Xác thực thành công",
                        "message": f"Đã kết nối thông suốt và xác thực chữ ký HMAC thành công tới Backend qua ({api_url})! Khóa bí mật khớp 100%.",
                        "type": "success",
                        "sticky": False,
                    }
                }
            elif resp.status_code == 401:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Lỗi xác thực (401 Unauthorized)",
                        "message": f"Kết nối tới máy chủ thành công nhưng XÁC THỰC THẤT BẠI: Khóa bí mật HMAC không khớp với cấu hình ODOO_SHARED_SECRET trên Backend! Vui lòng kiểm tra lại khóa.",
                        "type": "danger",
                        "sticky": True,
                    }
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Phản hồi mã lỗi",
                        "message": f"Máy chủ API phản hồi mã HTTP {resp.status_code} tại {test_url}.",
                        "type": "warning",
                        "sticky": False,
                    }
                }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Không thể kết nối API",
                    "message": f"Lỗi: {str(e)}. Gợi ý: Dùng 'http://host.docker.internal:5000/api/v1' cho Docker.",
                    "type": "danger",
                    "sticky": True,
                }
            }

    def action_open_batch_sync_wizard(self):
        """Mở wizard đồng bộ toàn bộ kho theo SKU từ cài đặt"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đồng bộ liên kết Website theo SKU',
            'res_model': 'qba.product.web.batch.sync.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'active_model': 'res.config.settings',
                'active_ids': [],
                'active_id': False,
                'default_mode': 'all_unlinked',
            }
        }

    def action_open_batch_unlink_wizard(self):
        """Mở popup xác nhận hủy liên kết toàn bộ kho với Website từ cài đặt"""
        linked_prods = self.env['product.template'].search([('is_website_linked', '=', True)])
        if not linked_prods:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Không có sản phẩm nào cần gỡ',
                    'message': 'Hiện tại không có sản phẩm nào trong kho đang được liên kết với Website.',
                    'type': 'info',
                    'sticky': False,
                }
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Xác nhận hủy liên kết Website toàn bộ kho',
            'res_model': 'qba.product.web.batch.unlink.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'active_model': 'product.template',
                'active_ids': linked_prods.ids,
                'default_product_tmpl_ids': [(6, 0, linked_prods.ids)],
            }
        }



