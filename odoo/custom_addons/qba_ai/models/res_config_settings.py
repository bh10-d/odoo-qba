# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gemini_api_key = fields.Char(
        string="Gemini API Key",
        config_parameter="qba_ai.gemini_api_key",
        help="Khóa API lấy từ Google AI Studio (aistudio.google.com)"
    )
    gemini_model_name = fields.Char(
        string="Mô hình Gemini",
        config_parameter="qba_ai.gemini_model_name",
        default="gemini-3.6-flash",
        help="Ví dụ: gemini-1.5-flash hoặc gemini-1.5-pro"
    )
    gemini_max_tokens = fields.Integer(
        string="Giới hạn Token đầu ra",
        config_parameter="qba_ai.gemini_max_tokens",
        default=8192,
        help="Giới hạn số token để tránh tiêu tốn nhiều dung lượng API"
    )
    ai_enable_cache = fields.Boolean(
        string="Bật bộ nhớ đệm (Cache)",
        config_parameter="qba_ai.enable_cache",
        default=True,
        help="Bật cache để sử dụng lại câu trả lời cho các câu hỏi trùng lặp"
    )
