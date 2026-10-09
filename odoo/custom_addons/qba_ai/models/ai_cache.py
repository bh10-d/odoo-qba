# -*- coding: utf-8 -*-
import hashlib
from datetime import datetime, timedelta
from odoo import models, fields, api

class QbaAiCache(models.Model):
    _name = "qba.ai.cache"
    _description = "Bộ Nhớ Đệm AI Request Cache"
    _order = "create_date desc"

    query_hash = fields.Char(string="MD5 Hash câu hỏi", required=True, index=True)
    query_text = fields.Text(string="Nội dung câu hỏi", required=True)
    response_json = fields.Text(string="Kết quả phản hồi (JSON/Text)", required=True)
    hit_count = fields.Integer(string="Số lần sử dụng lại cache", default=1)

    @api.model
    def get_cached_response(self, query_text):
        """Lấy phản hồi từ cache nếu trùng câu hỏi trong vòng 7 ngày"""
        clean_text = (query_text or "").strip().lower()
        if not clean_text:
            return False
        
        q_hash = hashlib.md5(clean_text.encode('utf-8')).hexdigest()
        seven_days_ago = fields.Datetime.now() - timedelta(days=7)
        
        cached = self.search([
            ('query_hash', '=', q_hash),
            ('create_date', '>=', seven_days_ago)
        ], limit=1)

        if cached and cached.response_json:
            # Nếu cache bị ngắt dở (dưới 100 ký tự hoặc không hợp lệ), bỏ qua cache cũ
            res_str = str(cached.response_json)
            if len(res_str) > 80 and not res_str.strip().endswith(('->', '- Bước', '...')):
                cached.hit_count += 1
                return cached.response_json
        return False

    @api.model
    def set_cached_response(self, query_text, response_json):
        """Lưu kết quả vào cache để không tốn lượt gọi Gemini API"""
        clean_text = (query_text or "").strip().lower()
        if not clean_text or not response_json:
            return
            
        q_hash = hashlib.md5(clean_text.encode('utf-8')).hexdigest()
        existing = self.search([('query_hash', '=', q_hash)], limit=1)
        if existing:
            existing.write({
                'response_json': response_json,
                'write_date': fields.Datetime.now()
            })
        else:
            self.create({
                'query_hash': q_hash,
                'query_text': query_text,
                'response_json': response_json
            })
