# -*- coding: utf-8 -*-
import logging
import re
import time
from odoo import models, fields, api, _
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)

class QbaAiAssistant(models.TransientModel):
    _name = "qba.ai.assistant"
    _description = "Trợ Lý AI Tra Cứu Phụ Tùng & Hướng Dẫn Đo"

    @api.model
    def _default_matching_html(self):
        return (
            "<div class='alert alert-light border p-4 text-center text-muted shadow-sm'>"
            "  <div class='mb-3'><i class='fa fa-balance-scale fa-3x text-primary'></i></div>"
            "  <h5 class='text-dark fw-bold mb-2'>Khu Vực Đối Chiếu Kỹ Thuật &amp; Phụ Tùng Thay Thế (Matching Engine)</h5>"
            "  <p class='mb-2 text-dark'>Hệ thống tự động so khớp thông số kỹ thuật đã duyệt (Verified) theo quy tắc dung sai và ràng buộc cốt lõi.</p>"
            "  <hr class='my-3 w-50 mx-auto'/>"
            "  <p class='small text-muted mb-1'><b>Hướng dẫn sử dụng:</b></p>"
            "  <p class='small text-muted mb-0'>Nhập mã sản phẩm (Ví dụ: <code>LC.001</code>, <code>LC.002</code>, <code>LC.007</code>) hoặc thông số (Ví dụ: <i>Lá côn 325mm 10 răng</i>) ở ô trên và nhấn <b>'Hỏi AI / Tra Cứu Ngay'</b>.</p>"
            "</div>"
        )

    @api.model
    def _default_ai_response(self):
        return (
            "<div class='alert alert-light border p-4 text-center text-muted shadow-sm'>"
            "  <div class='mb-3'><i class='fa fa-magic fa-3x text-primary'></i></div>"
            "  <h5 class='text-dark fw-bold mb-2'>Trợ Lý AI Tra Cứu &amp; Hướng Dẫn Kỹ Thuật</h5>"
            "  <p class='small text-muted mb-0'>Nhập câu hỏi quy trình đo đạc hoặc kỹ thuật phụ tùng ở ô trên và bấm <b>'Hỏi AI / Tra Cứu Ngay'</b> để nhận phản hồi từ AI.</p>"
            "</div>"
        )

    user_query = fields.Text(string="Nhập câu hỏi hoặc thông số cần đo / tra cứu", required=True)
    ai_response = fields.Html(string="Kết quả trả lời từ Trợ lý AI", readonly=True, default=_default_ai_response)
    matched_knowledge_ids = fields.Many2many('qba.ai.knowledge', string="Bài hướng dẫn đo liên quan", readonly=True)
    matched_product_ids = fields.Many2many('product.template', string="Sản phẩm phụ tùng gợi ý", readonly=True)
    confidence_level = fields.Selection([
        ('high', 'Độ tin cậy Cao'),
        ('medium', 'Độ tin cậy Trung Bình'),
        ('low', 'Độ tin cậy Thấp (Đã đưa vào hàng chờ Admin)')
    ], string="Độ tin cậy", readonly=True)
    status_message = fields.Char(string="Trạng thái xử lý", readonly=True)
    matching_explanation_html = fields.Html(string="Bảng đối chiếu thông số kỹ thuật (Matching)", readonly=True, default=_default_matching_html)
    query_perf_html = fields.Html(string="Thông tin xử lý truy vấn (Performance)", readonly=True)

    def action_ask_ai(self):
        """Hành động tra cứu AI & RAG với hệ thống định tuyến ý định và đo lường hiệu năng 8 công đoạn bằng Monotonic Clock"""
        self.ensure_one()
        query = (self.user_query or "").strip()
        if not query:
            return

        t_backend_start = time.perf_counter()
        req_id = f"REQ-{int(time.time() * 1000) % 1000000:06d}"

        # 1. Phân tích input & định tuyến ý định bằng Generic Query Intent Router
        t0 = time.perf_counter()
        router = self.env["qba.query.intent.router"]
        route_res = router.route_query(query)
        intent = route_res.get("intent")
        intent_label = route_res.get("intent_label")
        intent_badge = route_res.get("intent_badge_html")
        t_parse_input = time.perf_counter() - t0

        # Khởi tạo các biến đo lường và trạng thái
        matched_knowledges = self.env["qba.ai.knowledge"].browse()
        matched_products = self.env["product.template"].browse()
        matching_html = ""
        engine_timings = {}
        t_search_base = 0.0
        t_cand_retrieval = None
        t_load_specs = None
        t_eval_cands = None
        t_rank_explain = None
        t_ai = None
        ai_status = "skipped"
        ai_status_label = "Không thực hiện"
        confidence = "high"
        status_msg = "Tra cứu thành công"
        response_html = ""

        # =====================================================================
        # XỬ LÝ THEO TỪNG LOẠI Ý ĐỊNH (7 INTENTS)
        # =====================================================================

        # Case 1: Ambiguous Query (Mơ hồ, quá ngắn, không rõ ý định)
        if intent == "ambiguous":
            ai_status = "skipped"
            ai_status_label = "Bỏ qua (Yêu cầu chưa rõ ràng)"
            confidence = "low"
            clarification = route_res.get("clarification_message") or _("Vui lòng cung cấp thêm thông tin mã sản phẩm hoặc thông số kỹ thuật.")
            status_msg = "Yêu cầu chưa rõ ràng. Vui lòng cung cấp thêm thông tin."
            response_html = (
                f"<div class='alert alert-info border mb-3'>"
                f"  <div class='d-flex align-items-center mb-1'>{intent_badge}<h5 class='mb-0 ms-2'><i class='fa fa-question-circle text-primary me-2'></i>Yêu cầu chưa rõ ràng</h5></div>"
                f"  <p class='mb-1 text-dark'>{html_escape(clarification)}</p>"
                f"  <hr class='my-2'/>"
                f"  <div class='small text-muted'>"
                f"    <b>Gợi ý tra cứu:</b>"
                f"    <ul class='mb-0 ps-3'>"
                f"      <li>Tra cứu theo mã SKU: <code>LC.002</code>, <code>TBUA.010</code>, <code>BN-005</code>...</li>"
                f"      <li>Tra cứu theo thông số: <i>Lá côn 325mm 10 răng</i>, <i>Tăm bua 10 lỗ phi 420</i>...</li>"
                f"      <li>Tra cứu theo thiết bị: <i>Lá côn Howo 371</i>, <i>Bơm nước Yuchai 6L</i>...</li>"
                f"    </ul>"
                f"  </div>"
                f"</div>"
            )
            matching_html = (
                "<div class='alert alert-light border p-3 rounded mb-3'>"
                "  <p class='mb-0 text-muted small'><i class='fa fa-info-circle me-1'></i> Động cơ so khớp kỹ thuật tạm dừng vì chưa có mã sản phẩm hoặc thông số kỹ thuật rõ ràng để tiến hành đối chiếu.</p>"
                "</div>"
            )

        # Case 2: Exact SKU & Explicit Replacement (Tra cứu SKU chính xác hoặc tìm phụ tùng thay thế)
        elif intent in ("exact_sku", "explicit_replacement"):
            t1 = time.perf_counter()
            base_prod = route_res.get("target_product")
            if not base_prod:
                target_sku = route_res.get("target_sku") or route_res.get("clean_query")
                found_prods = self._search_products(target_sku or query)
                base_prod = found_prods[0] if found_prods else None

            if base_prod:
                matched_products = self.env["product.template"].browse([base_prod.id])
            else:
                matched_products = self._search_products(query)

            matched_knowledges = self._search_knowledge(query)
            t_search_base = time.perf_counter() - t1

            # Kích hoạt Matching Engine với sản phẩm cơ sở
            t_matching_start = time.perf_counter()
            matching_html, extra_products, engine_timings = self._generate_matching_explanation(query, matched_products)
            t_matching_total = time.perf_counter() - t_matching_start

            t_cand_retrieval = engine_timings.get("retrieval_sec") if engine_timings else None
            t_load_specs = engine_timings.get("specs_load_sec") if engine_timings else None
            t_eval_cands = engine_timings.get("eval_sec") if engine_timings else None
            t_rank_explain = engine_timings.get("rank_explain_sec") if engine_timings else None

            ai_status = "skipped"
            ai_status_label = "Không thực hiện (Đã hoàn tất đối chiếu nội bộ)"

            if matched_products:
                p_name = html_escape(matched_products[0].name)
                p_code = html_escape(matched_products[0].default_code or 'N/A')
                categ_name = html_escape(matched_products[0].categ_id.display_name or 'N/A')
                response_html = (
                    f"<div class='alert alert-success border mb-3'>"
                    f"  <div class='d-flex align-items-center mb-1'>{intent_badge}<h5 class='mb-0 ms-2'><i class='fa fa-check-circle text-success me-2'></i>Nhận diện phụ tùng: {p_name} [{p_code}]</h5></div>"
                    f"  <p class='mb-0 small text-muted'>Danh mục: <b>{categ_name}</b>. Hệ thống đã kích hoạt Động Cơ So Khớp Thông Số Kỹ Thuật (Generic Matching Engine) từ dữ liệu đã duyệt (Verified). Xem kết quả đối chiếu chi tiết tại tab <b>Bảng Đối Chiếu Kỹ Thuật (Matching)</b>.</p>"
                    f"</div>"
                )
                confidence = 'high'
                status_msg = f"Đã tìm thấy sản phẩm {p_code} & chạy đối chiếu kỹ thuật."
            else:
                response_html = (
                    f"<div class='alert alert-warning border mb-3'>"
                    f"  <div class='d-flex align-items-center mb-1'>{intent_badge}<h5 class='mb-0 ms-2'><i class='fa fa-exclamation-triangle text-warning me-2'></i>Không tìm thấy mã sản phẩm</h5></div>"
                    f"  <p class='mb-0 small text-muted'>Không tìm thấy sản phẩm có mã <code>{html_escape(route_res.get('target_sku') or query)}</code> trong kho QBA.</p>"
                    f"</div>"
                )
                confidence = 'low'
                status_msg = "Không tìm thấy mã sản phẩm trong kho."

        # Case 3: Technical Spec Only (Tra cứu thuần thông số kỹ thuật)
        elif intent == "technical_spec_only":
            t1 = time.perf_counter()
            matched_knowledges = self._search_knowledge(query)
            t_search_base = time.perf_counter() - t1

            # Kích hoạt Matching Engine trực tiếp từ thông số
            t_matching_start = time.perf_counter()
            matching_html, extra_products, engine_timings = self._generate_matching_explanation(query, matched_products=None)
            if extra_products:
                matched_products = extra_products
            t_matching_total = time.perf_counter() - t_matching_start

            t_cand_retrieval = engine_timings.get("retrieval_sec") if engine_timings else None
            t_load_specs = engine_timings.get("specs_load_sec") if engine_timings else None
            t_eval_cands = engine_timings.get("eval_sec") if engine_timings else None
            t_rank_explain = engine_timings.get("rank_explain_sec") if engine_timings else None

            ai_status = "skipped"
            ai_status_label = "Không thực hiện (Đối chiếu thông số trực tiếp)"
            specs_summary = ", ".join([f"{k}: {v.get('value')} {v.get('uom','')}" for k, v in route_res.get("extracted_specs", {}).items()])

            response_html = (
                f"<div class='alert alert-info border mb-3'>"
                f"  <div class='d-flex align-items-center mb-1'>{intent_badge}<h5 class='mb-0 ms-2'><i class='fa fa-sliders text-info me-2'></i>Tra cứu theo thông số kỹ thuật</h5></div>"
                f"  <p class='mb-1 small'><b>Thông số nhận diện:</b> {html_escape(specs_summary)}</p>"
                f"  <p class='mb-0 small text-muted'>Động Cơ So Khớp đã phân tích và thẩm định các thông số trên. Xem chi tiết tại tab <b>Bảng Đối Chiếu Kỹ Thuật (Matching)</b>.</p>"
                f"</div>"
            )
            confidence = 'high'
            status_msg = f"Đã đối chiếu thông số kỹ thuật ({len(route_res.get('extracted_specs', {}))} thông số)."

        # Case 4: General Search (Equipment Context, Product Name Alias, Natural Language Description)
        else:
            t1 = time.perf_counter()
            matched_knowledges = self._search_knowledge(query)
            matched_products = self._search_products(query)
            t_search_base = time.perf_counter() - t1

            ai_status = "skipped"
            ai_status_label = "Không thực hiện (Tìm kiếm nội bộ kho QBA)"

            # Tạo banner giải thích cho tab Matching: chưa kích hoạt vì đây là tìm kiếm danh mục/bối cảnh
            if matched_products:
                matching_html = (
                    "<div class='alert alert-light border p-3 rounded mb-3'>"
                    "  <div class='d-flex align-items-center mb-2'>"
                    "    <i class='fa fa-search fa-2x text-secondary me-3'></i>"
                    "    <div>"
                    "      <h5 class='mb-0 text-secondary'>Kết quả tìm kiếm phụ tùng trong kho QBA</h5>"
                    "      <span class='text-muted small'>Chưa kích hoạt đối chiếu thay thế kỹ thuật (Matching Engine)</span>"
                    "    </div>"
                    "  </div>"
                    "  <hr class='my-2'/>"
                    f"  <p class='mb-2 small'>Tìm thấy <b>{len(matched_products)}</b> sản phẩm phù hợp với từ khóa tra cứu.</p>"
                    "  <div class='bg-white p-2 border rounded small text-muted'>"
                    "    <i class='fa fa-info-circle me-1'></i><b>Lưu ý nghiệp vụ:</b> Đây là danh sách tìm kiếm thông thường theo tên phụ tùng hoặc bối cảnh xe/động cơ, <u>chưa được thẩm định tương thích thay thế</u>. Để tìm phụ tùng thay thế tương đương, vui lòng cung cấp mã sản phẩm gốc cần thay (Ví dụ: <i>Thay thế cho LC.002</i>) hoặc nhập thông số kỹ thuật chi tiết."
                    "  </div>"
                    "</div>"
                )
            else:
                matching_html = (
                    "<div class='alert alert-light border p-3 rounded mb-3'>"
                    "  <div class='d-flex align-items-center mb-2'>"
                    "    <i class='fa fa-search fa-2x text-secondary me-3'></i>"
                    "    <div>"
                    "      <h5 class='mb-0 text-secondary'>Kết quả tìm kiếm phụ tùng trong kho QBA</h5>"
                    "      <span class='text-muted small'>Chưa kích hoạt đối chiếu thay thế kỹ thuật (Matching Engine)</span>"
                    "    </div>"
                    "  </div>"
                    "  <hr class='my-2'/>"
                    "  <p class='mb-2 small'>Không có sản phẩm cơ sở để chạy thuật toán đối chiếu thông số (Tìm thấy 0 sản phẩm).</p>"
                    "  <div class='bg-white p-2 border rounded small text-muted'>"
                    "    <i class='fa fa-info-circle me-1'></i><b>Lưu ý nghiệp vụ:</b> Đây là danh sách tìm kiếm thông thường theo tên phụ tùng hoặc bối cảnh xe/động cơ, <u>chưa được thẩm định tương thích thay thế</u>. Để tìm phụ tùng thay thế tương đương, vui lòng cung cấp mã sản phẩm gốc cần thay (Ví dụ: <i>Thay thế cho LC.002</i>) hoặc nhập thông số kỹ thuật chi tiết."
                    "  </div>"
                    "</div>"
                )

            # Nếu có sản phẩm và intent là product_name_alias hoặc equipment_context mà không phải câu hỏi mở
            if matched_products and intent in ("product_name_alias", "equipment_context"):
                prod_cards = []
                for p in matched_products[:8]:
                    p_code = html_escape(p.default_code or 'N/A')
                    p_name = html_escape(p.name)
                    p_cat = html_escape(p.categ_id.display_name or 'N/A')
                    p_price = f"{p.list_price:,.0f} VNĐ" if p.list_price else "Liên hệ"
                    prod_cards.append(f"<li><b>[{p_code}]</b> {p_name} &mdash; <i>{p_cat}</i> ({p_price})</li>")

                prods_html = "<ul class='mb-0 ps-3 small'>" + "".join(prod_cards) + "</ul>"
                response_html = (
                    f"<div class='alert alert-light border mb-3'>"
                    f"  <div class='d-flex align-items-center mb-2'>{intent_badge}<h5 class='mb-0 ms-2'><i class='fa fa-cubes text-primary me-2'></i>Tìm thấy {len(matched_products)} sản phẩm trong kho QBA</h5></div>"
                    f"  {prods_html}"
                    f"  <div class='mt-2 small text-muted fst-italic'>Để so khớp phụ tùng thay thế, vui lòng nhập mã sản phẩm cụ thể (Ví dụ: <code>thay thế cho {html_escape(matched_products[0].default_code or '...')}</code>).</div>"
                    f"</div>"
                )
                confidence = 'high'
                status_msg = f"Đã tìm thấy {len(matched_products)} sản phẩm trong kho QBA."

            else:
                # Câu hỏi mở / hướng dẫn kỹ thuật / câu hỏi chung hoặc không tìm thấy sản phẩm -> Gọi Gemini AI
                knowledge_context = ""
                if matched_knowledges:
                    knowledge_context = "\n--- BÀI HƯỚNG DẪN TRONG KHO KIẾN THỨC ---\n"
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
                ai_service = self.env['qba.ai.service']
                t_ai_start = time.perf_counter()
                try:
                    res = ai_service.call_gemini_api(prompt)
                except Exception as e:
                    _logger.warning("QBA AI: Exception during AI call, falling back: %s", e)
                    res = {"error": f"Lỗi kết nối AI: {e}"}
                t_ai = time.perf_counter() - t_ai_start

                if "error" in res:
                    ai_status = "fallback"
                    ai_status_label = f"Fallback nội bộ ({t_ai:.2f}s)"
                    response_html = f"<div class='alert alert-warning'>{html_escape(res['error'])}</div>"
                    if matched_knowledges or matched_products:
                        response_html += "<h4>Kết quả tra cứu nội bộ từ DB:</h4>"
                    confidence = 'low'
                    status_msg = "Không kết nối được AI, đã sử dụng tìm kiếm nội bộ"
                else:
                    ai_status = "success"
                    ai_status_label = f"Thành công ({t_ai:.2f}s)"
                    response_html = res.get('text', '')
                    if matched_products or matched_knowledges:
                        confidence = 'high'
                        status_msg = f"Đã tìm thấy {len(matched_products)} sản phẩm & {len(matched_knowledges)} bài hướng dẫn phù hợp trong DB."
                    else:
                        confidence = 'medium'
                        status_msg = "Không thấy sản phẩm khớp 100% trong DB. AI đang gợi ý dựa trên tri thức chung."

        # Nếu độ tin cậy thấp hoặc lỗi -> Tự động đưa vào hàng chờ Admin
        if confidence == 'low' or (not matched_knowledges and not matched_products and len(query) > 10):
            self.env['qba.ai.approval.queue'].create({
                'name': f"Hỏi về: {query[:40]}...",
                'question': query,
                'suggested_answer': response_html,
                'reason': 'no_product_found' if not matched_products else 'low_confidence',
                'state': 'pending'
            })

        if matching_html:
            response_html += (
                "<div class='alert alert-light border mt-3 p-2 small'>"
                "<b><i class='fa fa-balance-scale me-1'></i> Bảng đối chiếu kỹ thuật:</b> "
                "Xem chi tiết phân tích thông số, dung sai và độ tương thích tại tab "
                "<b>Bảng Đối Chiếu Kỹ Thuật (Matching)</b>."
                "</div>"
            )

        # 8. Tổng thời gian backend
        t_total_backend = time.perf_counter() - t_backend_start

        # Tạo bảng Thông Tin Xử Lý Truy Vấn (Performance Metrics Table)
        try:
            perf_html = self._format_performance_metrics_html(
                req_id=req_id,
                t_parse=t_parse_input,
                t_search=t_search_base,
                t_retrieval=t_cand_retrieval,
                t_load_specs=t_load_specs,
                t_eval=t_eval_cands,
                t_rank_explain=t_rank_explain,
                t_ai=t_ai,
                t_total=t_total_backend,
                ai_status=ai_status_label,
                total_cands=engine_timings.get("total_candidates", len(matched_products)) if engine_timings else len(matched_products),
                total_matches=engine_timings.get("total_matches", len(matched_products)) if engine_timings else len(matched_products),
                intent_label=intent_label,
                intent_badge=intent_badge,
            )
        except Exception as e:
            _logger.error("QBA AI: Error generating performance metrics HTML: %s", e)
            perf_html = f"<div class='alert alert-warning'>Không thể hiển thị thông tin đo lường hiệu năng: {e}</div>"

        # Structured Logging
        _logger.info(
            "QBA AI Query Perf: req_id=%s query='%s' intent=%s total_backend=%.4fs parse=%.4fs search=%.4fs "
            "cand_retrieval=%s load_specs=%s eval_cands=%s rank_explain=%s ai_call=%s ai_status=%s",
            req_id, query[:30], intent, t_total_backend, t_parse_input, t_search_base,
            f"{t_cand_retrieval:.4f}s" if t_cand_retrieval is not None else "N/A",
            f"{t_load_specs:.4f}s" if t_load_specs is not None else "N/A",
            f"{t_eval_cands:.4f}s" if t_eval_cands is not None else "N/A",
            f"{t_rank_explain:.4f}s" if t_rank_explain is not None else "N/A",
            f"{t_ai:.4f}s" if t_ai is not None else "skipped",
            ai_status,
        )

        self.write({
            'ai_response': response_html,
            'matched_knowledge_ids': [(6, 0, matched_knowledges.ids)],
            'matched_product_ids': [(6, 0, matched_products.ids)],
            'confidence_level': confidence,
            'status_message': status_msg,
            'matching_explanation_html': matching_html,
            'query_perf_html': perf_html,
        })

        view = self.env.ref('qba_ai.view_qba_ai_assistant_form', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'qba.ai.assistant',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(view.id if view else False, 'form')],
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
            'views': [(False, 'form')],
            'target': 'current',
        }

    @api.model
    def _format_performance_metrics_html(self, req_id, t_parse, t_search, t_retrieval, t_load_specs, t_eval, t_rank_explain, t_ai, t_total, ai_status, total_cands=0, total_matches=0, intent_label=None, intent_badge=None):
        """Xây dựng bảng HTML hiển thị Thông Tin Xử Lý Truy Vấn chi tiết theo chuẩn Phase 4.3 Section 5.3"""
        def fmt_time(val):
            if val is None:
                return "<span class='text-muted'>Không thực hiện</span>"
            if val == 0 or val == 0.0:
                return "<b>0.000</b> s"
            if val < 0.001:
                return f"<b>&lt; 0.001</b> s ({val * 1000:.2f} ms)"
            return f"<b>{val:.3f}</b> s ({val * 1000:.1f} ms)"

        if t_search is None and t_retrieval is None:
            t_find_prod = None
        else:
            t_find_prod = (t_search or 0.0) + (t_retrieval or 0.0)

        if t_total is None:
            t_total_badge = "Không thực hiện"
            t_total_row = "<span class='text-muted'>Không thực hiện</span>"
        elif t_total < 0.001:
            t_total_badge = f"&lt; 0.001s ({t_total * 1000:.2f} ms)"
            t_total_row = f"<b>&lt; 0.001</b> s ({t_total * 1000:.2f} ms)"
        else:
            t_total_badge = f"{t_total:.3f}s"
            t_total_row = f"<b>{t_total:.3f}</b> s ({t_total * 1000:.1f} ms)"

        intent_row_title = f"1. Phân tích yêu cầu &amp; định tuyến ý định ({html_escape(intent_label)})" if intent_label else "1. Phân tích yêu cầu &amp; nhận diện SKU/thông số"
        intent_row_status = f"<div class='d-flex justify-content-center align-items-center gap-1'>{intent_badge}</div>" if intent_badge else "<span class='text-muted small'>Monotonic clock</span>"

        html = [
            "<div class='card mb-3 border-secondary-subtle shadow-sm' style='font-size: 0.9rem;'>",
            "  <div class='card-header bg-light d-flex justify-content-between align-items-center py-2'>",
            f"    <span><i class='fa fa-tachometer text-primary me-2'></i><b>Thông Tin Xử Lý Truy Vấn</b> <small class='text-muted'>(Mã: {html_escape(req_id)})</small></span>",
            f"    <span class='badge bg-success fs-7'>Tổng thời gian backend: {t_total_badge}</span>",
            "  </div>",
            "  <div class='card-body p-2'>",
            "    <table class='table table-sm table-hover mb-1 align-middle'>",
            "      <thead class='table-light'>",
            "        <tr>",
            "          <th style='width: 45%;'>Chỉ số công đoạn</th>",
            "          <th class='text-end' style='width: 25%;'>Thời gian</th>",
            "          <th class='text-center' style='width: 30%;'>Ghi chú / Trạng thái</th>",
            "        </tr>",
            "      </thead>",
            "      <tbody>",
            f"        <tr><td>{intent_row_title}</td><td class='text-end'>{fmt_time(t_parse)}</td><td class='text-center'>{intent_row_status}</td></tr>",
            f"        <tr><td>2. Tìm sản phẩm cơ sở &amp; ứng viên</td><td class='text-end'>{fmt_time(t_find_prod)}</td><td class='text-center text-muted small'>{total_cands} ứng viên</td></tr>",
            f"        <tr><td>3. Tải EAV Specs &amp; Quy tắc so khớp (N+1 Free)</td><td class='text-end'>{fmt_time(t_load_specs)}</td><td class='text-center text-muted small'>Batch prefetch</td></tr>",
            f"        <tr><td>4. Đánh giá ứng viên (Matching Engine Core)</td><td class='text-end'>{fmt_time(t_eval)}</td><td class='text-center text-muted small'>{total_matches} khớp</td></tr>",
            f"        <tr><td>5. Xếp hạng &amp; Tạo bảng giải thích HTML</td><td class='text-end'>{fmt_time(t_rank_explain)}</td><td class='text-center text-muted small'>Formatting</td></tr>",
            f"        <tr><td>6. Dịch vụ AI (Gemini External API)</td><td class='text-end'>{fmt_time(t_ai)}</td><td class='text-center small'><b>{html_escape(str(ai_status))}</b></td></tr>",
            f"        <tr class='table-light fw-bold'><td>TỔNG THỜI GIAN XỬ LÝ BACKEND</td><td class='text-end text-primary'>{t_total_row}</td><td class='text-center'><span class='badge bg-primary'>Backend Verified</span></td></tr>",
            "      </tbody>",
            "    </table>",
            "    <div class='text-muted small px-1 mt-1'>",
            "      <i class='fa fa-info-circle me-1'></i><i>Số liệu đo lường bằng monotonic clock (<code>time.perf_counter()</code>) tại máy chủ backend. Chưa bao gồm độ trễ mạng trình duyệt.</i>",
            "    </div>",
            "  </div>",
            "</div>",
        ]
        return "\n".join(html)

    def _render_rejected_candidates_html(self, rejected_cands, collapsible=False):
        """Hiển thị chi tiết bảng sản phẩm không đạt chuẩn, tách biệt rõ giữa mismatch và insufficient_data.
        Đặc biệt cho các sản phẩm như LC.007: hiển thị rõ thiếu moay-ơ C & D với giá trị yêu cầu và hard constraint note.
        """
        if not rejected_cands:
            return ""

        insufficient = [c for c in rejected_cands if c.get("match_status") == "insufficient_data"]
        mismatched = [c for c in rejected_cands if c.get("match_status") == "mismatch"]

        cards_html = []

        # 1. Nhóm chưa đủ dữ liệu xác thực (Insufficient Data)
        if insufficient:
            cards_html.append("<div class='card mb-3 border-secondary-subtle shadow-sm'>")
            cards_html.append("  <div class='card-header bg-light py-2'>")
            cards_html.append(f"    <strong class='text-secondary'><i class='fa fa-question-circle text-secondary me-1'></i> Nhóm Chưa Đủ Dữ Liệu Xác Thực ({len(insufficient)} sản phẩm)</strong>")
            cards_html.append("    <div class='small text-muted'>Chưa thể kết luận tương thích do thiếu số liệu đo đạc hoặc dữ liệu chưa được Quản trị viên duyệt (verified). Tuyệt đối không suy đoán.</div>")
            cards_html.append("  </div>")
            cards_html.append("  <div class='table-responsive'><table class='table table-sm table-hover mb-0 align-middle small'>")
            cards_html.append("    <thead class='table-light'><tr><th style='width: 15%;'>Mã SP</th><th style='width: 25%;'>Tên sản phẩm</th><th style='width: 15%;'>Trạng thái</th><th style='width: 45%;'>Thông số thiếu / Lý do kỹ thuật</th></tr></thead>")
            cards_html.append("    <tbody>")
            for c in insufficient:
                c_code = html_escape(str(c.get("candidate_code") or "N/A"))
                c_name = html_escape(str(c.get("candidate_name") or ""))
                missing_items = []
                for m in c.get("missing_critical_specs", []):
                    s_name = html_escape(str(m.get("spec_name") or m.get("spec_code") or ""))
                    in_v = f"{m['input_val']}" if m.get("input_val") is not None else ""
                    m_detail = f"<b>{s_name}</b>"
                    if in_v:
                        m_detail += f" (Y/c: <code>{html_escape(in_v)}</code> - SP: <i>Chưa có dữ liệu verified</i>)"
                    missing_items.append(m_detail)

                if missing_items:
                    detail_str = "<ul class='mb-0 ps-3'>" + "".join([f"<li>{item}</li>" for item in missing_items]) + "</ul>"
                    detail_str += "<div class='text-muted small mt-1'><i>Hard constraint: Không thể thay thế nếu chưa xác minh kích thước moay-ơ.</i></div>"
                else:
                    detail_str = html_escape(str(c.get("status_reason") or "Chưa có đủ thông số kỹ thuật cốt lõi"))

                cards_html.append(f"<tr><td><code>{c_code}</code></td><td>{c_name}</td><td><span class='badge bg-secondary'>Chưa đủ dữ liệu</span></td><td>{detail_str}</td></tr>")
            cards_html.append("    </tbody></table></div></div>")

        # 2. Nhóm không tương thích kỹ thuật (Mismatch)
        if mismatched:
            cards_html.append("<div class='card mb-3 border-danger-subtle shadow-sm'>")
            cards_html.append("  <div class='card-header bg-danger bg-opacity-10 py-2'>")
            cards_html.append(f"    <strong class='text-danger'><i class='fa fa-times-circle text-danger me-1'></i> Nhóm Không Tương Thích Kỹ Thuật ({len(mismatched)} sản phẩm)</strong>")
            cards_html.append("    <div class='small text-muted'>Đã xác minh có sai lệch kích thước hoặc vi phạm điều kiện bắt buộc (Hard Constraints) không thể bù trừ.</div>")
            cards_html.append("  </div>")
            cards_html.append("  <div class='table-responsive'><table class='table table-sm table-hover mb-0 align-middle small'>")
            cards_html.append("    <thead class='table-light'><tr><th style='width: 15%;'>Mã SP</th><th style='width: 25%;'>Tên sản phẩm</th><th style='width: 15%;'>Trạng thái</th><th style='width: 45%;'>Thông số vi phạm / Lý do loại trừ</th></tr></thead>")
            cards_html.append("    <tbody>")
            for c in mismatched:
                c_code = html_escape(str(c.get("candidate_code") or "N/A"))
                c_name = html_escape(str(c.get("candidate_name") or ""))
                viol_items = []
                for v in c.get("violated_hard_constraints", []):
                    s_name = html_escape(str(v.get("spec_name") or v.get("spec_code") or ""))
                    in_v = html_escape(str(v.get("input_val"))) if v.get("input_val") is not None else "-"
                    cand_v = html_escape(str(v.get("candidate_val"))) if v.get("candidate_val") is not None else "-"
                    delta_v = f"{v['delta']:+g}" if v.get("delta") is not None else ""
                    viol_items.append(f"<b>{s_name}</b> (Y/c: <code>{in_v}</code>, SP: <code>{cand_v}</code>, Lệch: <code>{delta_v}</code>)")

                if viol_items:
                    detail_str = "<ul class='mb-0 ps-3 text-danger'>" + "".join([f"<li>{item}</li>" for item in viol_items]) + "</ul>"
                else:
                    detail_str = f"<span class='text-danger'>{html_escape(str(c.get('status_reason') or 'Vi phạm điều kiện bắt buộc'))}</span>"

                if c.get("has_missing_data"):
                    detail_str += "<div class='text-muted small mt-1'><i>(Lưu ý: Ứng viên này đồng thời thiếu một số dữ liệu xác thực)</i></div>"

                cards_html.append(f"<tr><td><code>{c_code}</code></td><td>{c_name}</td><td><span class='badge bg-danger'>Không tương thích</span></td><td>{detail_str}</td></tr>")
            cards_html.append("    </tbody></table></div></div>")

        content = "\n".join(cards_html)
        if collapsible:
            return (
                f"<details class='mt-3 p-2 bg-light border rounded small'>"
                f"  <summary class='text-secondary fw-bold' style='cursor: pointer;'><i class='fa fa-list me-1'></i> Xem {len(rejected_cands)} sản phẩm cùng danh mục bị từ chối đề xuất (Phân loại chi tiết Mismatch / Insufficient Data)</summary>"
                f"  <div class='mt-2'>{content}</div>"
                f"</details>"
            )
        return content

    def _generate_matching_explanation(self, query, matched_products):
        """Xây dựng bảng đối chiếu kỹ thuật HTML (Matching Explanation) chi tiết:
        - Xử lý 100% các kịch bản tra cứu nghiệp vụ:
          1. Tìm kiếm bằng sản phẩm có thông số verified -> Chạy Matching Engine -> Hiển thị thông số gốc, bảng xếp hạng tương thích & dung sai.
          2. Tìm kiếm bằng sản phẩm chưa có thông số verified -> Cảnh báo rõ ràng và giải thích nguyên tắc an toàn dữ liệu QBA.
          3. Nhập trực tiếp thông số kỹ thuật (ví dụ 'Lá côn 325mm 10 răng') -> Trích xuất thông số, xác định danh mục & chạy Matching Engine.
          4. Không có sản phẩm cơ sở và không có thông số hợp lệ -> Hiển thị trạng thái giải thích và hướng dẫn tra cứu.
        - Đảm bảo an toàn XSS (html_escape) và định dạng trực quan.
        - Trả về tuple (matching_html, extra_matched_products, engine_timings)
        """
        engine = self.env["qba.spec.matching.engine"]

        # 1. Kịch bản: Có sản phẩm tìm thấy trong kho
        if matched_products:
            target_prod = matched_products[0]
            if not target_prod.categ_id:
                return (
                    "<div class='alert alert-warning border p-3 rounded mb-3'>"
                    "<h5 class='text-warning-emphasis mb-1'><i class='fa fa-exclamation-circle me-2'></i> Chưa phân loại danh mục</h5>"
                    f"<p class='mb-0'>Sản phẩm <b>{html_escape(target_prod.display_name)}</b> chưa được gán danh mục để thực hiện so khớp thông số kỹ thuật.</p>"
                    "</div>",
                    None,
                    None
                )

            # Kiểm tra xem danh mục của sản phẩm có profile hoặc quy tắc so khớp không
            profile = engine.resolve_profile(target_prod.categ_id)
            rules_count = len(profile.rule_ids) if hasattr(profile, "rule_ids") else len(profile.get("rule_dicts", []))
            if rules_count == 0:
                return (
                    f"<div class='alert alert-info border p-3 rounded mb-3'>"
                    f"  <div class='d-flex align-items-center mb-2'>"
                    f"    <i class='fa fa-info-circle fa-2x text-primary me-3'></i>"
                    f"    <div>"
                    f"      <h5 class='mb-0 text-dark'>Danh mục chưa có Hồ sơ so khớp kỹ thuật</h5>"
                    f"      <span class='text-muted small'>Sản phẩm cơ sở: <b>{html_escape(target_prod.display_name)}</b></span>"
                    f"    </div>"
                    f"  </div>"
                    f"  <hr class='my-2'/>"
                    f"  <p class='mb-1'><b>Danh mục:</b> {html_escape(target_prod.categ_id.display_name)}</p>"
                    f"  <p class='mb-0 small text-muted'>Danh mục này hiện chưa được cấu hình Hồ sơ so khớp kỹ thuật (Matching Profile) hoặc định nghĩa thông số. Vui lòng cấu hình tại <b>Cấu hình &gt; Hồ sơ so khớp</b> trước khi thực hiện tìm phụ tùng thay thế tương đương.</p>"
                    f"</div>",
                    None,
                    None
                )

            verified_vals = target_prod.spec_value_ids.filtered(
                lambda v: v.validation_status == "verified" and v.spec_definition_id.active
            )

            # Kịch bản 1A: Sản phẩm có thông số kỹ thuật đã duyệt (Verified)
            if verified_vals:
                try:
                    matching_res = engine.match_product_to_candidates(target_prod.id, options={"limit": 10})
                except Exception as e:
                    _logger.warning("Lỗi khi gọi match_product_to_candidates: %s", e)
                    matching_res = {"success": False, "error": str(e)}

                if matching_res.get("success"):
                    engine_timings = matching_res.get("timing", {})
                    html = []
                    # Hộp thông tin sản phẩm gốc & thông số đã duyệt
                    html.append("<div class='card mb-3 border-primary shadow-sm'>")
                    html.append("  <div class='card-header bg-primary text-white d-flex justify-content-between align-items-center py-2'>")
                    html.append(f"    <span class='fw-bold'><i class='fa fa-cube me-1'></i> Sản phẩm cơ sở: {html_escape(target_prod.name)}</span>")
                    html.append(f"    <span class='badge bg-light text-primary fs-7'>Mã: {html_escape(target_prod.default_code or 'N/A')}</span>")
                    html.append("  </div>")
                    html.append("  <div class='card-body p-3'>")
                    html.append("    <div class='row mb-2 small text-muted'>")
                    html.append(f"      <div class='col-sm-6'><b>Danh mục:</b> {html_escape(target_prod.categ_id.display_name)}</div>")
                    html.append(f"      <div class='col-sm-6'><b>Hồ sơ đối chiếu:</b> {html_escape(str(matching_res.get('profile_name', 'Tiêu chuẩn mặc định')))}</div>")
                    html.append("    </div>")
                    html.append("    <div class='table-responsive'>")
                    html.append("      <table class='table table-sm table-bordered mb-0 align-middle small'>")
                    html.append("        <thead class='table-light'>")
                    html.append("          <tr>")
                    html.append("            <th>Thông số kỹ thuật gốc</th>")
                    html.append("            <th>Giá trị đã duyệt</th>")
                    html.append("            <th>Đơn vị tính</th>")
                    html.append("            <th>Ràng buộc kỹ thuật</th>")
                    html.append("          </tr>")
                    html.append("        </thead>")
                    html.append("        <tbody>")
                    for val in verified_vals:
                        v_disp = val.value_display or str(engine._get_typed_spec_value(val))
                        crit_badge = "<span class='badge bg-danger'>Cốt lõi (Bắt buộc)</span>" if val.is_critical else "<span class='badge bg-secondary'>Tiêu chuẩn</span>"
                        html.append(
                            f"          <tr>"
                            f"            <td><b>{html_escape(val.spec_definition_id.name)}</b></td>"
                            f"            <td class='fw-bold text-primary'>{html_escape(v_disp)}</td>"
                            f"            <td>{html_escape(val.uom or '-')}</td>"
                            f"            <td>{crit_badge}</td>"
                            f"          </tr>"
                        )
                    html.append("        </tbody>")
                    html.append("      </table>")
                    html.append("    </div>")
                    html.append("  </div>")
                    html.append("</div>")

                    ranked_matches = matching_res.get("ranked_matches", [])
                    rejected_cands = matching_res.get("rejected_candidates", [])
                    total_cand = matching_res.get("total_candidates", 0)
                    total_match = matching_res.get("total_matches", 0)
                    engine_timings["total_candidates"] = total_cand
                    engine_timings["total_matches"] = total_match

                    if ranked_matches:
                        html.append("<div class='alert alert-success d-flex align-items-center py-2 px-3 mb-3'>")
                        html.append("  <i class='fa fa-check-circle fa-2x text-success me-3'></i>")
                        html.append("  <div>")
                        html.append(f"    <strong class='fs-6'>Đã tìm thấy {total_match} phụ tùng thay thế tương thích kỹ thuật trong kho QBA!</strong><br/>")
                        html.append(f"    <span class='small text-muted'>Đã thẩm định {total_cand} sản phẩm ứng viên cùng danh mục theo tiêu chuẩn dung sai &amp; ràng buộc cốt lõi.</span>")
                        html.append("  </div>")
                        html.append("</div>")

                        for match in ranked_matches:
                            html.append(engine.format_explanation(match))

                        if rejected_cands:
                            html.append(self._render_rejected_candidates_html(rejected_cands, collapsible=True))
                    else:
                        html.append("<div class='alert alert-warning mb-3 p-3 rounded'>")
                        html.append("  <div class='d-flex align-items-center mb-2'>")
                        html.append("    <i class='fa fa-info-circle fa-2x text-warning me-3'></i>")
                        html.append("    <div>")
                        html.append("      <h6 class='alert-heading fw-bold mb-0'>Không tìm thấy phụ tùng thay thế tương thích trong cùng danh mục</h6>")
                        html.append(f"      <span class='small text-muted'>Đã quét toàn bộ {total_cand} sản phẩm trong danh mục {html_escape(target_prod.categ_id.display_name)}.</span>")
                        html.append("    </div>")
                        html.append("  </div>")
                        html.append("  <p class='small mb-2'>Không có sản phẩm nào thỏa mãn các ràng buộc cốt lõi hoặc khoảng dung sai an toàn để thay thế cho sản phẩm này.</p>")
                        html.append("</div>")
                        if rejected_cands:
                            html.append(self._render_rejected_candidates_html(rejected_cands, collapsible=False))

                    return ("\n".join(html), None, engine_timings)
                else:
                    return (
                        matching_res.get("explanation_html") or f"<div class='alert alert-info py-2 mb-2'>{html_escape(matching_res.get('error') or _('Không thể chạy đối chiếu kỹ thuật'))}</div>",
                        None,
                        matching_res.get("timing")
                    )

            # Kịch bản 1B: Sản phẩm tìm thấy nhưng CHƯA có thông số verified
            return (
                "<div class='alert alert-warning border border-warning p-3 rounded mb-3'>"
                "  <div class='d-flex align-items-center mb-2'>"
                "    <i class='fa fa-exclamation-triangle fa-2x text-warning me-3'></i>"
                "    <div>"
                "      <h5 class='mb-0 text-dark'>Sản phẩm tìm thấy chưa có thông số kỹ thuật đã duyệt (verified)</h5>"
                "      <span class='text-muted small'>Cơ chế bảo vệ dữ liệu kỹ thuật QBA</span>"
                "    </div>"
                "  </div>"
                "  <hr class='my-2'/>"
                f"  <p class='mb-1'><b>Sản phẩm:</b> {html_escape(target_prod.display_name)} [Mã: <code>{html_escape(target_prod.default_code or 'N/A')}</code>]</p>"
                f"  <p class='mb-1'><b>Danh mục:</b> {html_escape(target_prod.categ_id.display_name)}</p>"
                "  <p class='mb-2 text-danger fw-bold'>Trạng thái: Sản phẩm chưa có thông số kỹ thuật đã duyệt (verified) trong kho để thực hiện đối chiếu tự động.</p>"
                "  <div class='bg-white p-2 border rounded small mb-2 text-muted'>"
                "    <b>Tại sao cần duyệt (Verified)?</b>"
                "    <p class='mb-0'>Theo nguyên tắc an toàn kỹ thuật phụ tùng QBA, Matching Engine nghiêm ngặt chỉ dựa trên các thông số đã được nhân viên kỹ thuật thẩm định (trạng thái <code>verified</code>). Điều này nhằm ngăn ngừa tuyệt đối rủi ro tư vấn sai quy cách hoặc sai kích thước lắp ráp cho khách hàng.</p>"
                "  </div>"
                "  <div class='small'>"
                "    <b>Quy trình xử lý an toàn:</b>"
                "    <ol class='mb-0 ps-3'>"
                f"      <li>Kỹ thuật viên thực hiện đo đạc thực tế chính xác kích thước và thông số vật lý của sản phẩm <b>{html_escape(target_prod.name)}</b>.</li>"
                "      <li>Nhập số liệu đo đạc vào tab <b>Thông số kỹ thuật</b> của sản phẩm và thẩm định kỹ lưỡng trước khi bấm <b>Duyệt (Verify)</b>. <i>Tuyệt đối không duyệt khi chưa có số liệu đo đạc thực tế.</i></li>"
                "      <li>Sau khi thông số được thẩm định và duyệt, quay lại đây bấm <b>Hỏi AI / Tra Cứu Ngay</b> để tự động nhận bảng đối chiếu phụ tùng thay thế.</li>"
                "    </ol>"
                "  </div>"
                "</div>",
                None,
                None
            )

        # 2. Kịch bản: Người dùng nhập trực tiếp thông số kỹ thuật (ví dụ "Lá côn 325mm 10 răng", "325-10R", "rang: 10")
        direct_specs_res = self._try_direct_spec_matching(query)
        if direct_specs_res:
            return direct_specs_res

        # 3. Kịch bản Fallback: Không tìm thấy sản phẩm cơ sở và không có thông số hợp lệ
        return (
            "<div class='alert alert-info border p-3 rounded mb-3'>"
            "  <div class='d-flex align-items-center mb-2'>"
            "    <i class='fa fa-info-circle fa-2x text-primary me-3'></i>"
            "    <div>"
            "      <h5 class='mb-0 text-primary'>Trạng thái Đối Chiếu Kỹ Thuật (Matching Engine)</h5>"
            "      <span class='text-muted small'>Chưa có thông số đầu vào để so khớp</span>"
            "    </div>"
            "  </div>"
            "  <hr class='my-2'/>"
            "  <p class='mb-2 text-dark'>Không có sản phẩm cơ sở để chạy thuật toán đối chiếu thông số.</p>"
            "  <p class='mb-1 small fw-bold'>Để sử dụng chức năng đối chiếu thông số kỹ thuật tự động:</p>"
            "  <ul class='mb-0 small ps-3 text-muted'>"
            "    <li>Nhập mã phụ tùng / SKU cụ thể có trong hệ thống (Ví dụ: <code>LC.001</code>, <code>LC.002</code>, <code>LC.007</code>...).</li>"
            "    <li>Nhập tên danh mục kèm thông số kỹ thuật cần tìm (Ví dụ: <i>Lá côn 325mm 10 răng</i>, <i>Lá côn phi 350 10R</i>...).</li>"
            "    <li>Hoặc tra cứu quy trình đo kỹ thuật ở tab <b>Bài Hướng Dẫn Đo Liên Quan</b> để xác định thông số chuẩn trước khi tra cứu.</li>"
            "  </ul>"
            "</div>",
            None,
            None
        )

    def _try_direct_spec_matching(self, query):
        """Phân tích thông số kỹ thuật đa danh mục bằng Generic Query Intent Router và kích hoạt Matching Engine"""
        engine = self.env["qba.spec.matching.engine"]
        router = self.env["qba.query.intent.router"]

        category = router._detect_category(query)
        parsed_specs = router._extract_technical_specs(query, category=category)

        if not parsed_specs:
            return False

        if not category:
            html = [
                "<div class='alert alert-warning border-warning p-3 rounded mb-3'>",
                "  <div class='d-flex align-items-center mb-2'>",
                "    <i class='fa fa-exclamation-triangle fa-2x text-warning me-3'></i>",
                "    <div>",
                f"      <h5 class='mb-0 text-dark'>{_('Chưa xác định danh mục phụ tùng')}</h5>",
                f"      <span class='text-muted small'>{_('Hệ thống nhận diện được thông số kỹ thuật: ')}<b>{html_escape(', '.join(parsed_specs.keys()))}</b></span>",
                "    </div>",
                "  </div>",
                "  <p class='mb-1 small text-dark'>" + _("Để đối chiếu phụ tùng thay thế chính xác, vui lòng nhập tên danh mục kèm thông số (Ví dụ: <i>Lá côn 325mm 10 răng</i>, <i>Tăm bua 10 lỗ</i>, <i>Bi moay ơ...</i>).") + "</p>",
                "</div>"
            ]
            return ("\n".join(html), None, None)

        try:
            matching_res = engine.find_matching_products(category.id, parsed_specs, options={"limit": 10})
        except Exception as e:
            _logger.warning("Lỗi find_matching_products trực tiếp: %s", e)
            return False

        if not matching_res.get("has_profile", True) or not matching_res.get("success"):
            expl_html = matching_res.get("explanation_html") or f"<div class='alert alert-info py-2 mb-2'>{html_escape(matching_res.get('error') or _('Danh mục chưa có hồ sơ đối chiếu'))}</div>"
            return (expl_html, None, matching_res.get("timing"))

        ranked_matches = matching_res.get("ranked_matches", [])
        total_cand = matching_res.get("total_candidates", 0)
        total_match = matching_res.get("total_matches", 0)
        insufficient_cands = matching_res.get("insufficient_candidates", [])
        rejected_cands = matching_res.get("rejected_candidates", [])
        engine_timings = matching_res.get("timing", {})
        engine_timings["total_candidates"] = total_cand
        engine_timings["total_matches"] = total_match

        html = []
        html.append("<div class='card mb-3 border-success shadow-sm'>")
        html.append("  <div class='card-header bg-success text-white py-2'>")
        html.append("    <span class='fw-bold'><i class='fa fa-sliders me-1'></i> Đối Chiếu Kỹ Thuật Trực Tiếp Từ Yêu Cầu</span>")
        html.append("  </div>")
        html.append("  <div class='card-body p-3'>")
        html.append(f"    <p class='mb-1 small'><b>Danh mục nhận diện:</b> {html_escape(category.display_name)}</p>")
        specs_summary = ", ".join([f"{k}: <b>{v['value']} {v.get('uom','')}</b>" for k, v in parsed_specs.items()])
        html.append(f"    <p class='mb-2 small'><b>Thông số yêu cầu:</b> {specs_summary}</p>")
        html.append("  </div>")
        html.append("</div>")

        matched_products = self.env["product.template"].browse()
        if ranked_matches:
            matched_products = self.env["product.template"].browse([m["candidate_id"] for m in ranked_matches if m.get("candidate_id")])
            html.append("<div class='alert alert-success d-flex align-items-center py-2 px-3 mb-3'>")
            html.append("  <i class='fa fa-check-circle fa-2x text-success me-3'></i>")
            html.append("  <div>")
            html.append(f"    <strong class='fs-6'>Tìm thấy {total_match} sản phẩm trong kho QBA phù hợp đầy đủ các thông số yêu cầu!</strong><br/>")
            html.append(f"    <span class='small text-muted'>Đã thẩm định {total_cand} sản phẩm trong danh mục.</span>")
            html.append("  </div>")
            html.append("</div>")
            for match in ranked_matches:
                html.append(engine.format_explanation(match))
            if rejected_cands:
                html.append(self._render_rejected_candidates_html(rejected_cands, collapsible=True))
        elif insufficient_cands:
            html.append("<div class='alert alert-info border-info d-flex align-items-center py-2 px-3 mb-3'>")
            html.append("  <i class='fa fa-info-circle fa-2x text-info me-3'></i>")
            html.append("  <div>")
            html.append(f"    <strong class='fs-6'>Tìm thấy {len(insufficient_cands)} sản phẩm khớp thông số đã cung cấp (Chưa đủ dữ liệu xác nhận tương thích tổng thể)</strong><br/>")
            html.append(f"    <span class='small text-muted'>Yêu cầu kỹ thuật hiện tại mới đối chiếu {len(parsed_specs)} thông số. Danh mục {html_escape(category.display_name)} yêu cầu đủ các thông số cốt lõi để đảm bảo khả năng lắp ráp thay thế.</span>")
            html.append("  </div>")
            html.append("</div>")
            for match in insufficient_cands[:10]:
                html.append(engine.format_explanation(match))
            if rejected_cands:
                html.append(self._render_rejected_candidates_html(rejected_cands, collapsible=True))
        else:
            html.append("<div class='alert alert-warning mb-3 p-3 rounded'>")
            html.append("  <h6 class='alert-heading fw-bold mb-1'><i class='fa fa-info-circle me-1'></i> Không có sản phẩm phù hợp</h6>")
            html.append(f"  <p class='small mb-0'>Đã quét toàn bộ {total_cand} sản phẩm trong kho nhưng chưa có sản phẩm nào thỏa mãn các thông số yêu cầu trên.</p>")
            html.append("</div>")
            if rejected_cands:
                html.append(self._render_rejected_candidates_html(rejected_cands, collapsible=False))

        return ("\n".join(html), matched_products, engine_timings)

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

        # Chuẩn hóa các cụm danh từ đồng nghĩa phổ biến trong phụ tùng tiếng Việt
        raw_clean = re.sub(r'\bvòng\s+bi\b', 'bi', raw_clean, flags=re.I)
        raw_clean = re.sub(r'\bbạc\s+đạn\b', 'bi', raw_clean, flags=re.I)

        # 1. Trích xuất Mã Kỹ Thuật / Model Code (như 6123, 4102, MC07, 8JS85T, DTNC.002, BAPD.035, LC.001...)
        raw_candidates = re.findall(r'\b[A-Za-z]+[0-9\.-]+[A-Za-z0-9\.-]*\b|\b[0-9\.-]+[A-Za-z]+[A-Za-z0-9\.-]*\b|\b\d{3,}(?:[.,]\d+)?\b|\b[A-Z0-9\.-]{4,}\b', raw_clean)
        model_codes = []
        for c in raw_candidates:
            clean_code = re.sub(r'(?:mm|cm|kg|g|r|v)$', '', c, flags=re.I)
            if clean_code and clean_code not in model_codes:
                model_codes.append(clean_code)

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
                    else:
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
