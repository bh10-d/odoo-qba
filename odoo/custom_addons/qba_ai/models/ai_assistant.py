# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class QbaAiAssistant(models.TransientModel):
    _name = "qba.ai.assistant"
    _description = "Trợ Lý AI Tra Cứu Phụ Tùng & Hướng Dẫn Đo"

    user_query = fields.Text(string="Nhập câu hỏi hoặc thông số cần đo / tra cứu", required=True)
    ai_response = fields.Html(string="Kết quả trả lời từ Trợ lý AI", readonly=True)
    matched_knowledge_ids = fields.Many2many('qba.ai.knowledge', string="Bài hướng dẫn đo liên quan", readonly=True)
    matched_product_ids = fields.Many2many('product.template', string="Sản phẩm phụ tùng gợi ý", readonly=True)
    confidence_level = fields.Selection([
        ('high', 'Độ tin cậy Cao'),
        ('medium', 'Độ tin cậy Trung Bình'),
        ('low', 'Độ tin cậy Thấp (Đã đưa vào hàng chờ Admin)')
    ], string="Độ tin cậy", readonly=True)
    status_message = fields.Char(string="Trạng thái xử lý", readonly=True)

    def action_ask_ai(self):
        """Hành động tra cứu AI & RAG"""
        self.ensure_one()
        query = (self.user_query or "").strip()
        if not query:
            return

        # 1. Tra cứu bài viết Kiến Thức Đo Lường trong DB
        matched_knowledges = self._search_knowledge(query)
        
        # 2. Tra cứu Sản phẩm phụ tùng khớp trong DB
        matched_products = self._search_products(query)

        # 3. Chuẩn bị Context cho RAG
        knowledge_context = ""
        if matched_knowledges:
            knowledge_context = "\n--- BÀI HƯỚNG DẪN ĐO TRONG KHO KIẾN THỨC ---\n"
            for k in matched_knowledges:
                knowledge_context += f"- {k.name}: {k.summary or k.content[:200]}\n"

        product_context = ""
        if matched_products:
            product_context = "\n--- SẢN PHẨM KHỚP TRONG KHO QBA ---\n"
            for p in matched_products[:5]:
                product_context += f"- {p.name} (SKU/Mã: {p.default_code or 'N/A'}, Giá: {p.list_price} VNĐ)\n"

        prompt = f"""
Câu hỏi của nhân viên: "{query}"

{knowledge_context}
{product_context}

Nhiệm vụ của bạn:
1. Trả lời hướng dẫn nhân viên cách đo đạc thông số kỹ thuật (nếu là câu hỏi về đo đạc).
2. Tóm tắt danh sách sản phẩm khớp thông số (nếu có).
3. Nếu thông số chưa rõ ràng, đưa ra 1-2 câu hỏi gợi ý để nhân viên đo bổ sung.
Phản hồi trình bày rõ ràng dạng HTML (dùng <h4>, <ul>, <li>, <b>).
"""

        # 4. Gọi Gemini AI Service
        ai_service = self.env['qba.ai.service']
        res = ai_service.call_gemini_api(prompt)

        response_html = ""
        confidence = 'high'
        status_msg = "Tra cứu thành công"

        if "error" in res:
            response_html = f"<div class='alert alert-warning'>{res['error']}</div>"
            if matched_knowledges or matched_products:
                response_html += "<h4>Kết quả tra cứu nội bộ từ DB:</h4>"
            confidence = 'low'
            status_msg = "Không kết nối được AI, đã sử dụng tìm kiếm nội bộ"
        else:
            response_html = res.get('text', '')
            if matched_products or matched_knowledges:
                confidence = 'high'
                status_msg = f"Đã tìm thấy {len(matched_products)} sản phẩm & {len(matched_knowledges)} bài hướng dẫn phù hợp trong DB."
            else:
                confidence = 'medium'
                status_msg = "Không thấy sản phẩm khớp 100% trong DB. AI đang gợi ý dựa trên tri thức chung."

        # 5. Nếu độ tin cậy thấp hoặc lỗi -> Tự động đưa vào hàng chờ Admin
        if confidence == 'low' or (not matched_knowledges and not matched_products and len(query) > 10):
            self.env['qba.ai.approval.queue'].create({
                'name': f"Hỏi về: {query[:40]}...",
                'question': query,
                'suggested_answer': response_html,
                'reason': 'no_product_found' if not matched_products else 'low_confidence',
                'state': 'pending'
            })
            status_msg += " (Đã tạo yêu cầu Admin kiểm tra & cập nhật kiến thức)"

        self.write({
            'ai_response': response_html,
            'matched_knowledge_ids': [(6, 0, matched_knowledges.ids)],
            'matched_product_ids': [(6, 0, matched_products.ids)],
            'confidence_level': confidence,
            'status_message': status_msg
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'qba.ai.assistant',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_send_to_admin(self):
        """Gửi câu hỏi này lên hàng chờ Admin thủ công"""
        self.ensure_one()
        self.env['qba.ai.approval.queue'].create({
            'name': f"Nhân viên gửi: {self.user_query[:40]}...",
            'question': self.user_query,
            'suggested_answer': self.ai_response,
            'reason': 'manual_flag',
            'state': 'pending'
        })
        self.status_message = "Đã gửi lên Hàng chờ Admin phê duyệt thành công!"
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'qba.ai.assistant',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _search_knowledge(self, query):
        """Tìm kiếm bài viết hướng dẫn đo đạc linh hoạt"""
        import re
        raw_clean = re.sub(r'[^\w\s\.-]', ' ', query).strip()
        tokens = [t for t in raw_clean.split() if len(t) >= 2]
        
        found_knowledge = self.env['qba.ai.knowledge'].browse()
        for token in tokens:
            domain = ['|', '|', ('name', 'ilike', token), ('keywords', 'ilike', token), ('summary', 'ilike', token)]
            recs = self.env['qba.ai.knowledge'].search(domain, limit=5)
            found_knowledge |= recs
            
        return found_knowledge[:5]

    def _search_products(self, query):
        """
        Thuật toán Tìm kiếm Phụ tùng CHÍNH XÁC & KHÔNG GƯỢNG ÉP:
        - KHÔNG tự gom 10 sản phẩm rác để lấp đầy danh sách.
        - Nếu tìm thấy 1 hoặc 3 sản phẩm khớp chính xác -> CHỈ trả về đúng 1 hoặc 3 sản phẩm đó.
        - Nếu không có sản phẩm nào khớp -> Trả về 0 sản phẩm (rỗng) để AI thông báo hết kho.
        """
        import re
        raw_clean = re.sub(r'[^\w\s\.-]', ' ', query).strip()
        if not raw_clean:
            return self.env['product.template'].browse()

        # 1. Trích xuất Mã Kỹ Thuật / Model Code (như 6123, 4102, MC07, 8JS85T, DTNC.002, BAPD.035...)
        model_codes = re.findall(r'\b(?=.*\d)[A-Za-z0-9\.-]{2,}\b|\b[A-Z0-9\.-]{4,}\b', raw_clean)
        if model_codes:
            found_by_code = self.env['product.template'].browse()
            for code in model_codes:
                domain_code = ['|', '|', '|',
                    ('name', 'ilike', code),
                    ('default_code', 'ilike', code),
                    ('brand_sku', 'ilike', code),
                    ('brand_id.name', 'ilike', code)
                ]
                recs = self.env['product.template'].search(domain_code, limit=20)
                if recs:
                    # Nếu có từ mô tả đi kèm (ví dụ 'Bộ hơi MC07' hoặc 'Bánh răng bơm WP10')
                    text_terms = [t for t in raw_clean.split() if t not in model_codes and len(t) >= 2]
                    if text_terms:
                        # BẮT BUỘC sản phẩm phải chứa TẤT CẢ các từ mô tả (ví dụ cả 'bộ' VÀ 'hơi')
                        matched_strict = recs.filtered(lambda p: all(t.lower() in (p.name or '').lower() or t.lower() in (p.default_code or '').lower() for t in text_terms))
                        if matched_strict:
                            return matched_strict[:10]
                    found_by_code |= recs
            if found_by_code:
                return found_by_code[:10]

        # 2. Loại bỏ các từ giao tiếp / từ phụ tiếng Việt (giữ lại các danh từ phụ tùng quan trọng như 'bộ')
        stop_words = {
            'hãy', 'hay', 'hướng', 'huong', 'dẫn', 'dan', 'chi', 'tiết', 'tiet', 'quy', 'trình', 'trinh',
            'kiểm', 'kiem', 'tra', 'và', 'va', 'đo', 'do', 'đạc', 'dac', 'kỹ', 'ky', 'thuật', 'thuat',
            'trước', 'truoc', 'khi', 'thay', 'thế', 'the', 'cho', 'khong', 'không', 'co', 'có', 'anh',
            'toi', 'tôi', 'ban', 'bạn', 'em', 'loai', 'loại', 'tim', 'tìm', 'giup', 'giúp',
            'xem', 'duoc', 'được', 'nao', 'nào', 'voi', 'với', 'trong', 'kho', 'hoi', 'hỏi', 'thi', 'thì',
            'về', 've', 'của', 'cua', 'đang', 'dang', 'lại', 'lai', 'ở', 'tại', 'nay', 'quả', 'qua',
            'cái', 'cai', 'chiếc', 'chiec', 'gì', 'gi', 'này', 'nay'
        }

        tokens = [t for t in raw_clean.split() if len(t) >= 2 and t.lower() not in stop_words]
        if not tokens:
            tokens = [t for t in raw_clean.split() if len(t) >= 2]

        # 3. Tìm kiếm theo Cụm từ đầy đủ trước (Full Phrase Match)
        phrase_clean = " ".join(tokens)
        if len(phrase_clean) >= 3:
            domain_phrase = ['|', '|', '|',
                ('name', 'ilike', phrase_clean),
                ('default_code', 'ilike', phrase_clean),
                ('brand_sku', 'ilike', phrase_clean),
                ('brand_id.name', 'ilike', phrase_clean)
            ]
            recs_phrase = self.env['product.template'].search(domain_phrase, limit=10)
            if recs_phrase:
                return recs_phrase

        # 4. Tìm sản phẩm BẮT BUỘC chứa đồng thời tất cả các từ khóa quan trọng (Strict AND Match)
        if len(tokens) >= 2:
            and_domain = [('name', 'ilike', t) for t in tokens]
            recs_and = self.env['product.template'].search(and_domain, limit=10)
            if recs_and:
                return recs_and

        # 5. Fallback từ đơn lẻ: CHỈ dùng khi người dùng nhập đúng 1 từ đặc trưng (Ví dụ: 'Samtin', 'Yuchai')
        if len(tokens) == 1:
            token = tokens[0]
            if len(token) >= 3:
                domain_token = ['|', '|', '|',
                    ('name', 'ilike', token),
                    ('default_code', 'ilike', token),
                    ('brand_sku', 'ilike', token),
                    ('brand_id.name', 'ilike', token)
                ]
                recs_token = self.env['product.template'].search(domain_token, limit=10)
                if recs_token:
                    return recs_token

        # 6. Tuyệt đối KHÔNG gượng ép lấy sản phẩm không liên quan -> Trả về 0 sản phẩm rỗng!
        return self.env['product.template'].browse()
