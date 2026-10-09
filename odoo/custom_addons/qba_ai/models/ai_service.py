# -*- coding: utf-8 -*-
import json
import logging
import requests
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class QbaAiService(models.AbstractModel):
    _name = "qba.ai.service"
    _description = "Dịch Vụ Kết Nối Gemini AI với Cơ Chế An Toàn Quota"

    @api.model
    def get_api_key(self):
        """Lấy API Key từ Config Parameter"""
        key = self.env['ir.config_parameter'].sudo().get_param('qba_ai.gemini_api_key')
        return key or False

    @api.model
    def call_gemini_api(self, prompt, system_instruction=None):
        """
        Hàm gọi Gemini API an toàn với:
        - Kiểm tra Cache trước
        - Giới hạn maxOutputTokens=800
        - Timeout 10s
        - Error Handling & Fallback
        """
        api_key = self.get_api_key()
        if not api_key:
            return {"error": "Thiếu Gemini API Key. Vui lòng cấu hình trong Cài đặt."}

        # 1. Kiểm tra Cache xem đã có câu trả lời chưa
        enable_cache = self.env['ir.config_parameter'].sudo().get_param('qba_ai.enable_cache', default='True') == 'True'
        if enable_cache:
            cache_model = self.env['qba.ai.cache']
            cached_res = cache_model.get_cached_response(prompt)
            if cached_res:
                _logger.info("QBA AI: Trả về kết quả từ Cache cho câu hỏi '%s'", prompt[:30])
                try:
                    return json.loads(cached_res)
                except Exception:
                    return {"text": cached_res}

        # 2. Kiểm tra và tự động cập nhật mô hình Gemini hoạt động tốt nhất
        configured_model = self.env['ir.config_parameter'].sudo().get_param('qba_ai.gemini_model_name')
        if not configured_model or 'gemini-1.5' in configured_model or 'gemini-2.0' in configured_model or 'high' in configured_model:
            configured_model = 'gemini-3.5-flash'
            self.env['ir.config_parameter'].sudo().set_param('qba_ai.gemini_model_name', 'gemini-3.5-flash')

        candidate_models = [
            configured_model,
            'gemini-3.5-flash',
            'gemini-3.6-flash',
            'gemini-3.8-flash',
            'gemini-3.7-flash',
            'gemini-3.5-flash-lite'
        ]
        
        # Loại bỏ các tên trùng lặp nhưng vẫn giữ đúng thứ tự
        model_list = []
        for m in candidate_models:
            if m and m not in model_list:
                model_list.append(m)

        max_tokens_param = self.env['ir.config_parameter'].sudo().get_param('qba_ai.gemini_max_tokens')
        if not max_tokens_param or int(max_tokens_param) < 8192:
            self.env['ir.config_parameter'].sudo().set_param('qba_ai.gemini_max_tokens', '8192')
            max_tokens = 8192
        else:
            max_tokens = int(max_tokens_param)

        headers = {'Content-Type': 'application/json'}

        default_sys_instruction = (
            "Bạn là trợ lý AI chuyên gia phụ tùng ô tô QBA. "
            "Nhiệm vụ của bạn là phân tích yêu cầu của nhân viên, hướng dẫn chi tiết cách đo đạc thông số kỹ thuật (đường kính, số răng, moay ơ, chiều dài), "
            "hoặc trích xuất từ khóa sản phẩm để tìm kiếm trong kho. "
            "Hãy trình bày câu trả lời thật chi tiết, có cấu trúc rõ ràng (dùng HTML: <h4>, <ul>, <li>, <b>), không cắt dở nội dung."
        )

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction or default_sys_instruction}]
            },
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": max_tokens,
                "topP": 0.9
            }
        }

        # 3. Thực hiện Request thử qua danh sách mô hình
        last_error = ""
        for model_name in model_list:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    res_data = response.json()
                    try:
                        text_output = res_data['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError):
                        text_output = "Không nhận được phản hồi từ AI."

                    result = {"text": text_output, "raw": res_data}
                    
                    # Lưu cache
                    if enable_cache and text_output:
                        self.env['qba.ai.cache'].set_cached_response(prompt, json.dumps(result))
                        
                    return result
                elif response.status_code in (404, 503, 500, 502):
                    _logger.warning("QBA AI: Mô hình %s không khả dụng hoặc bị quá tải (Mã %s). Đang tự động chuyển sang mô hình tiếp theo...", model_name, response.status_code)
                    last_error = response.text
                    continue
                elif response.status_code == 429:
                    _logger.warning("QBA AI: Quá giới hạn Rate Limit / Quota Gemini API (429)")
                    return {
                        "error": "Đã đạt giới hạn số lượt gọi Gemini API miễn phí (Rate limit). Vui lòng thử lại sau 1 phút.",
                        "is_rate_limit": True
                    }
                else:
                    _logger.error("QBA AI API Error %s với model %s: %s", response.status_code, model_name, response.text)
                    last_error = f"Mã {response.status_code}: {response.text}"
            except requests.exceptions.Timeout:
                _logger.error("QBA AI: Gemini API request timed out (12s) với model %s", model_name)
                return {"error": "Hệ thống AI không phản hồi kịp thời (Timeout 12s). Chuyển sang tìm kiếm dữ liệu nội bộ."}
            except Exception as e:
                _logger.error("QBA AI: Exception during API call: %s", str(e))
                return {"error": f"Lỗi kết nối: {str(e)}"}

        return {"error": f"Không tìm thấy mô hình Gemini khả dụng. Lỗi chi tiết: {last_error}"}
