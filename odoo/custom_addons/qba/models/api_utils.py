# -*- coding: utf-8 -*-
import time
import hmac
import hashlib

DEFAULT_ODOO_API_SECRET = "qba_odoo_enterprise_m2m_hmac_secret_2026_super_secure"

def get_odoo_api_headers(env):
    """
    Tạo headers bảo mật gửi sang Express API với chữ ký điện tử HMAC-SHA256 và Timestamp.
    Ngăn chặn việc truyền khóa thô qua mạng và chống Replay Attack.
    """
    secret = env['ir.config_parameter'].sudo().get_param('qba.website_api_secret') or DEFAULT_ODOO_API_SECRET
    secret = secret.strip()
    timestamp = str(int(time.time()))
    signature = hmac.new(secret.encode('utf-8'), timestamp.encode('utf-8'), hashlib.sha256).hexdigest()

    return {
        'Content-Type': 'application/json',
        'x-odoo-timestamp': timestamp,
        'x-odoo-signature': signature,
    }

