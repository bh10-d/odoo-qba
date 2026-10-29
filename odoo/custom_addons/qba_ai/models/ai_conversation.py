# -*- coding: utf-8 -*-
import json
import logging
import re
import time
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)


class QbaAiConversation(models.Model):
    _name = "qba.ai.conversation"
    _description = "Phiên Hội Thoại Trợ Lý AI Tìm Kiếm Phụ Tùng"
    _order = "last_message_date desc, id desc"

    name = fields.Char(
        string="Tiêu đề hội thoại",
        default="Hội thoại mới",
        required=True
    )
    user_id = fields.Many2one(
        "res.users",
        string="Người dùng",
        required=True,
        default=lambda self: self.env.user,
        index=True
    )
    company_id = fields.Many2one(
        "res.company",
        string="Công ty",
        required=True,
        default=lambda self: self.env.company
    )
    is_active = fields.Boolean(
        string="Đang hoạt động",
        default=True,
        index=True
    )
    state = fields.Selection(
        [
            ("active", "Đang hoạt động"),
            ("archived", "Đã lưu trữ"),
        ],
        string="Trạng thái",
        default="active",
        index=True,
    )
    context_product_id = fields.Many2one(
        "product.template",
        string="Sản phẩm ngữ cảnh",
        index=True,
        help="Sản phẩm đang được người dùng xem hoặc chọn làm mốc đối chiếu trong phiên hội thoại"
    )
    context_product_name = fields.Char(
        string="Tên sản phẩm ngữ cảnh",
        related="context_product_id.name",
        readonly=True
    )
    context_product_code = fields.Char(
        string="Mã SKU ngữ cảnh",
        related="context_product_id.default_code",
        readonly=True
    )
    search_context_json = fields.Text(
        string="Ngữ cảnh tìm kiếm nhiều lượt (JSON)",
        default="{}",
        help="Lưu trữ cấu trúc thông số, danh mục, thương hiệu và bộ lọc qua các lượt chat"
    )
    message_ids = fields.One2many(
        "qba.ai.message",
        "conversation_id",
        string="Danh sách tin nhắn"
    )
    message_count = fields.Integer(
        string="Số lượng tin nhắn",
        compute="_compute_message_count"
    )
    last_message_date = fields.Datetime(
        string="Tin nhắn cuối",
        default=fields.Datetime.now,
        index=True
    )

    @api.depends("message_ids")
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    # =========================================================================
    # QUẢN LÝ VÒNG ĐỜI PHIÊN HỘI THOẠI (LIFECYCLE & SECURITY)
    # =========================================================================

    @api.model
    def get_or_create_active_conversation(self, context_product_id=None, conversation_id=None):
        """Lấy phiên hội thoại đang hoạt động của người dùng hiện tại, hoặc nạp chính xác theo conversation_id.
        Bảo đảm phân quyền chặt chẽ (chỉ người dùng sở hữu hoặc AI Manager mới có quyền truy cập).
        """
        user = self.env.user
        if conversation_id:
            conv = self.browse(int(conversation_id)).exists()
            if not conv:
                raise ValidationError(_("Phiên hội thoại không tồn tại hoặc đã bị xóa."))
            conv.check_access('read')
            if conv.user_id != user and not user.has_group("qba_ai.group_qba_ai_manager"):
                raise AccessError(_("Bạn không có quyền truy cập phiên hội thoại của người dùng khác."))
            # Đặt làm phiên active cho người dùng hiện tại nếu là chủ sở hữu
            self.search([
                ("user_id", "=", user.id),
                ("id", "!=", conv.id),
                ("is_active", "=", True)
            ]).write({"is_active": False})
            if conv.user_id == user:
                conv.write({"is_active": True})
            return conv

        # Khi không chỉ định ID (ví dụ bấm Launcher nổi): Lấy phiên active gần nhất của user
        domain = [
            ("user_id", "=", user.id),
            ("is_active", "=", True)
        ]
        conv = self.search(domain, order="last_message_date desc, id desc", limit=1)

        # Kiểm tra sản phẩm ngữ cảnh nếu client truyền lên
        prod = False
        if context_product_id:
            try:
                prod = self.env["product.template"].browse(int(context_product_id)).exists()
                prod.check_access('read')
            except Exception:
                prod = False

        if not conv:
            # Nếu chưa có phiên active, tìm phiên unarchived gần nhất
            conv = self.search([
                ("user_id", "=", user.id),
                ("state", "=", "active"),
            ], order="last_message_date desc, id desc", limit=1)
            if conv:
                conv.write({"is_active": True})
            else:
                title = _("Tra cứu: %s") % (prod.display_name or _("Tìm kiếm phụ tùng")) if prod else _("Hội thoại mới")
                conv = self.create({
                    "name": title,
                    "user_id": user.id,
                    "state": "active",
                    "is_active": True,
                    "context_product_id": prod.id if prod else False,
                    "search_context_json": json.dumps({"active_product_id": prod.id} if prod else {}),
                })
            # Gửi tin nhắn chào mừng khởi đầu
            conv._send_initial_greeting()
        elif prod and conv.context_product_id != prod:
            # Cập nhật sản phẩm ngữ cảnh nếu người dùng chuyển sang xem sản phẩm khác
            conv.write({
                "context_product_id": prod.id,
                "last_message_date": fields.Datetime.now(),
            })
            # Cập nhật search context
            ctx = conv._get_search_context()
            ctx["active_product_id"] = prod.id
            if prod.categ_id:
                ctx["active_category_id"] = prod.categ_id.id
                ctx["active_category_name"] = prod.categ_id.complete_name
            conv._save_search_context(ctx)

        return conv

    @api.model
    def get_user_conversations_history(self, limit=30):
        """Lấy danh sách các phiên hội thoại cũ của người dùng để hiển thị trên Drawer và view Lịch sử."""
        user = self.env.user
        domain = [("user_id", "=", user.id)] if not user.has_group("qba_ai.group_qba_ai_manager") else []
        convs = self.search(domain, order="last_message_date desc, id desc", limit=limit)
        res = []
        for c in convs:
            res.append({
                "id": c.id,
                "name": c.name or _("Hội thoại mới"),
                "create_date": c.create_date.strftime("%d/%m/%Y %H:%M") if c.create_date else "",
                "last_message_date": c.last_message_date.strftime("%d/%m/%Y %H:%M") if c.last_message_date else "",
                "message_count": c.message_count,
                "is_active": c.is_active,
                "state": c.state,
                "context_product_id": c.context_product_id.id if c.context_product_id else False,
                "context_product_name": c.context_product_id.display_name if c.context_product_id else "",
            })
        return res

    def action_open_in_drawer(self):
        """Mở phiên hội thoại này trong Trợ lý QBA AI Drawer."""
        self.ensure_one()
        self.check_access('read')
        # Kích hoạt phiên hội thoại này cho user hiện tại nếu là chủ sở hữu
        self.env["qba.ai.conversation"].search([
            ("user_id", "=", self.env.user.id),
            ("id", "!=", self.id),
            ("is_active", "=", True)
        ]).write({"is_active": False})
        if self.user_id == self.env.user:
            self.write({"is_active": True})
        return {
            "type": "ir.actions.client",
            "tag": "qba_ai_assistant_open",
            "params": {
                "conversation_id": self.id,
                "product_id": self.context_product_id.id if self.context_product_id else False,
            }
        }

    @api.model
    def create_new_conversation(self, context_product_id=None):
        """Bắt đầu một cuộc hội thoại mới sạch sẽ, lưu trữ cuộc hội thoại cũ."""
        user = self.env.user
        # Tắt cờ active các phiên cũ của user này
        old_convs = self.search([("user_id", "=", user.id), ("is_active", "=", True)])
        old_convs.write({"is_active": False, "state": "archived"})

        prod = False
        if context_product_id:
            try:
                prod = self.env["product.template"].browse(int(context_product_id)).exists()
                prod.check_access('read')
            except Exception:
                prod = False

        title = _("Tra cứu: %s") % (prod.display_name or _("Tìm kiếm phụ tùng")) if prod else _("Hội thoại mới")
        new_conv = self.create({
            "name": title,
            "user_id": user.id,
            "context_product_id": prod.id if prod else False,
            "search_context_json": json.dumps({"active_product_id": prod.id} if prod else {}),
            "is_active": True,
            "state": "active",
        })
        new_conv._send_initial_greeting()
        return new_conv

    def action_archive(self):
        """Lưu trữ hội thoại"""
        self.check_access('write')
        self.write({"is_active": False, "state": "archived"})
        return True

    def action_restore(self):
        """Khôi phục hội thoại từ trạng thái lưu trữ về đang hoạt động."""
        self.check_access('write')
        self.write({"state": "active"})
        return True

    def action_delete(self):
        """Xóa vĩnh viễn cuộc hội thoại và đóng cửa sổ/thông báo."""
        self.check_access('unlink')
        for rec in self:
            rec.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Đã xóa"),
                "message": _("Cuộc hội thoại đã được xóa thành công."),
                "type": "info",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            }
        }


    def get_search_context(self):
        """Lấy từ điển ngữ cảnh tìm kiếm hiện tại"""
        self.ensure_one()
        return self._get_search_context()

    def clear_context_product(self):
        """Xóa sản phẩm ngữ cảnh khỏi phiên hội thoại để quay về chế độ tìm kiếm toàn catalog."""
        self.ensure_one()
        self.check_access('write')
        self.write({"context_product_id": False})
        ctx = self._get_search_context()
        ctx.pop("active_product_id", None)
        self._save_search_context(ctx)
        return self.get_conversation_data()

    def set_context_product(self, product_id):
        """Gán sản phẩm ngữ cảnh mới cho phiên hội thoại."""
        self.ensure_one()
        self.check_access('write')
        prod = self.env["product.template"].browse(int(product_id)).exists()
        prod.check_access('read')
        self.write({"context_product_id": prod.id})
        ctx = self._get_search_context()
        ctx["active_product_id"] = prod.id
        if prod.categ_id:
            ctx["active_category_id"] = prod.categ_id.id
            ctx["active_category_name"] = prod.categ_id.complete_name
        self._save_search_context(ctx)
        return self.get_conversation_data()

    def get_conversation_data(self):
        """Trả về toàn bộ dữ liệu phiên hội thoại bao gồm lịch sử tin nhắn và ngữ cảnh."""
        self.ensure_one()
        self.check_access('read')
        ctx = self._get_search_context()
        messages_data = [msg.to_dict() for msg in self.message_ids]
        
        prod_data = None
        if self.context_product_id:
            p = self.context_product_id
            prod_data = {
                "id": p.id,
                "name": p.name,
                "default_code": p.default_code or "",
                "category_name": p.categ_id.complete_name or "",
            }

        return {
            "success": True,
            "conversation_id": self.id,
            "name": self.name,
            "state": self.state or "active",
            "is_active": self.is_active,
            "context_product": prod_data,
            "search_context": ctx,
            "message_count": len(messages_data),
            "messages": [msg.to_dict() for msg in self.message_ids.sorted('id')],
        }

    to_dict = get_conversation_data

    # =========================================================================
    # CORE MULTI-TURN SEARCH ENGINE & CONVERSATION ORCHESTRATOR
    # =========================================================================

    def post_user_message(self, content, context_product_id=None):
        """Phương thức trọng tâm: Tiếp nhận câu hỏi người dùng, phân tích ngữ cảnh nhiều lượt (Multi-turn),
        thực thi tìm kiếm phụ tùng toàn catalog hoặc đối chiếu kỹ thuật, và trả về phản hồi có cấu trúc.
        """
        self.ensure_one()
        self.check_access('write')

        raw_query = (content or "").strip()
        if not raw_query:
            raise ValidationError(_("Nội dung tin nhắn không được để trống."))

        t_backend_start = time.perf_counter()
        req_id = f"REQ-{int(time.time() * 1000) % 1000000:06d}"

        # Cập nhật sản phẩm ngữ cảnh nếu client gửi lên
        if context_product_id:
            try:
                prod = self.env["product.template"].browse(int(context_product_id)).exists()
                prod.check_access('read')
                if self.context_product_id != prod:
                    self.context_product_id = prod.id
            except Exception:
                pass

        # 1. Lưu tin nhắn của Người Dùng vào DB
        user_msg = self.env["qba.ai.message"].create({
            "conversation_id": self.id,
            "user_id": self.env.user.id,
            "role": "user",
            "content": raw_query,
        })

        # Đặt lại tên cuộc hội thoại theo câu hỏi đầu tiên
        if len(self.message_ids) <= 2 and self.name in (_("Hội thoại mới"), "Hội thoại mới"):
            short_title = raw_query[:40] + ("..." if len(raw_query) > 40 else "")
            self.name = short_title

        # 2. Đọc ngữ cảnh tìm kiếm đã lưu từ các lượt trước
        search_ctx = self._get_search_context()

        # 3. Phân tích truy vấn bằng Generic Query Intent Router
        t0 = time.perf_counter()
        router = self.env["qba.query.intent.router"]
        active_cat_id = search_ctx.get("active_category_id")
        active_cat = self.env["product.category"].browse(active_cat_id).exists() if active_cat_id else None
        route_res = router.route_query(raw_query, context_category=active_cat)
        t_parse = time.perf_counter() - t0

        intent = route_res.get("intent")
        intent_label = route_res.get("intent_label")
        intent_badge = route_res.get("intent_badge_html")

        # 4. Hợp nhất ngữ cảnh tìm kiếm đa lượt (Multi-turn Context Merger)
        merged_ctx = self._merge_multiturn_context(raw_query, route_res, search_ctx)

        # 5. Thực thi tìm kiếm và đối chiếu sản phẩm theo ngữ cảnh hợp nhất
        t1 = time.perf_counter()
        if intent == "ambiguous" and route_res.get("clarification_message"):
            search_results = {
                "mode": "ambiguous",
                "products": self.env["product.template"].browse(),
                "clarification": route_res.get("clarification_message"),
            }
        else:
            search_results = self._execute_conversational_search(merged_ctx, raw_query)
        t_search = time.perf_counter() - t1

        # 6. Chuẩn bị thẻ thông tin sản phẩm (Product Cards Payload)
        matched_prods = search_results.get("products", self.env["product.template"].browse())
        product_cards = self._build_product_cards(matched_prods, merged_ctx)

        # 7. Xây dựng câu trả lời đàm thoại (Conversational Summary)
        t2 = time.perf_counter()
        conversational_text = self._synthesize_conversational_response(
            query=raw_query,
            intent=intent,
            merged_ctx=merged_ctx,
            search_results=search_results,
            product_cards=product_cards
        )
        t_ai = time.perf_counter() - t2

        # 8. Tính toán hiệu năng và lưu tin nhắn phản hồi của Assistant
        t_total = time.perf_counter() - t_backend_start
        perf_data = {
            "req_id": req_id,
            "total_backend_sec": round(t_total, 4),
            "parse_sec": round(t_parse, 4),
            "search_sec": round(t_search, 4),
            "ai_synthesis_sec": round(t_ai, 4),
            "matched_count": len(product_cards),
        }

        # Lưu ngữ cảnh tìm kiếm cập nhật cho các lượt sau
        self._save_search_context(merged_ctx)
        self.last_message_date = fields.Datetime.now()

        # Phân loại rõ ràng loại phản hồi của assistant (Explicit Response Metadata)
        if search_results.get("mode") in ("compare", "replacement") and search_results.get("base_product"):
            msg_type = "search_result"
        elif len(product_cards) == 0 and intent != "ambiguous":
            msg_type = "search_empty"
        else:
            msg_type = "search_result"
        assistant_msg = self.env["qba.ai.message"].create({
            "conversation_id": self.id,
            "user_id": self.env.user.id,
            "role": "assistant",
            "message_type": msg_type,
            "content": conversational_text,
            "matched_product_ids": [(6, 0, matched_prods.ids)],
            "matched_products_json": json.dumps(product_cards, ensure_ascii=False),
            "explanation_html": search_results.get("matching_explanation_html") or "",
            "perf_info_json": json.dumps(perf_data),
            "intent": intent,
            "intent_label": intent_label,
            "intent_badge_html": intent_badge,
        })

        return self.get_conversation_data()

    # =========================================================================
    # MULTI-TURN CONTEXT MANAGEMENT & MERGER
    # =========================================================================

    def _get_search_context(self):
        """Đọc từ điển trạng thái tìm kiếm từ JSON an toàn."""
        try:
            return json.loads(self.search_context_json or "{}")
        except Exception:
            return {}

    def _save_search_context(self, ctx_dict):
        """Lưu lại từ điển trạng thái tìm kiếm an toàn."""
        self.search_context_json = json.dumps(ctx_dict, ensure_ascii=False)

    def _merge_multiturn_context(self, query, route_res, prev_ctx):
        """Bộ hợp nhất ngữ cảnh tìm kiếm đa lượt (Smart Multi-turn Context Merger):
        Phân biệt giữa:
        1. Bổ sung điều kiện (Adding Condition): e.g. "thêm 8 lò xo", "răng 10", "chỉ Antek".
        2. So sánh sản phẩm (Comparing): e.g. "so sánh với LC.002".
        3. Yêu cầu tìm phụ tùng thay thế cho sản phẩm đang xem/vừa tìm (Substitute Request).
        4. Bắt đầu tìm kiếm danh mục/chủ đề mới (New Search Topic): xóa các thông số danh mục cũ.
        """
        q_lower = query.lower()
        new_ctx = dict(prev_ctx or {})
        specs_in_ctx = dict(new_ctx.get("specs") or {})

        # Nhận diện hành vi bổ sung điều kiện
        is_additive = bool(re.search(r'\b(thêm|bổ\s+sung|cộng\s+thêm|và|với|yêu\s+cầu|chỉ\s+lấy)\b', q_lower))
        
        # Nhận diện ý định so sánh
        is_compare = bool(re.search(r'\b(so\s+sánh|khác\s+nhau|đối\s+chiếu|giống\s+nhau)\b', q_lower))
        if is_compare:
            new_ctx["mode"] = "compare"
        elif not is_additive:
            new_ctx.pop("mode", None)

        # Trích xuất thương hiệu (Brand filter)
        brand_match = re.search(r'\b(?:hãng|hiệu|thương\s+hiệu|của|chỉ)\s+([A-Za-z0-9\-]+)\b', query, re.I)
        if brand_match:
            new_ctx["brand"] = brand_match.group(1).strip()
        elif "chỉ lấy" in q_lower or "chỉ chọn" in q_lower:
            tokens = [t for t in query.split() if t.lower() not in ("chỉ", "lấy", "hàng", "của", "chọn")]
            if tokens:
                new_ctx["brand"] = tokens[-1].strip()

        # Kiểm tra nếu router trích xuất được danh mục mới
        target_cat = route_res.get("target_category")
        if target_cat and not is_additive:
            cat_id = target_cat.id
            if new_ctx.get("active_category_id") and new_ctx.get("active_category_id") != cat_id:
                # Chuyển sang danh mục mới: Xóa các thông số cũ không thuộc danh mục này
                specs_in_ctx = {}
            new_ctx["active_category_id"] = cat_id
            new_ctx["active_category_name"] = target_cat.complete_name

        # Cập nhật thông số kỹ thuật mới bóc tách được
        extracted_specs = route_res.get("extracted_specs")
        if isinstance(extracted_specs, dict) and extracted_specs:
            # Gộp thông số vào ngữ cảnh hiện tại
            for k, v in extracted_specs.items():
                specs_in_ctx[k] = v

        # Quản lý unresolved_numerics qua các lượt hội thoại
        prev_unresolved = new_ctx.get("unresolved_numerics") or []
        curr_unresolved = route_res.get("unresolved_numerics") or []
        all_unresolved = [n for n in prev_unresolved if n not in curr_unresolved] + curr_unresolved

        # Thử phân giải số chưa gán nhãn nếu hiện tại đã có danh mục hoặc thông số đặc trưng
        eff_cat_id = new_ctx.get("active_category_id")
        if not eff_cat_id and specs_in_ctx:
            defs = self.env['qba.product.spec.definition'].search([('code', 'in', list(specs_in_ctx.keys()))])
            cand_cats = defs.mapped('category_ids')
            if len(cand_cats) == 1:
                eff_cat_id = cand_cats[0].id
                new_ctx["active_category_id"] = eff_cat_id
                new_ctx["active_category_name"] = cand_cats[0].complete_name

        if all_unresolved and eff_cat_id:
            eff_cat = self.env["product.category"].browse(eff_cat_id)
            eff_cat_name = (eff_cat.name or "").lower()
            if "lc" in eff_cat_name or "lá côn" in eff_cat_name or "đĩa ly hợp" in eff_cat_name:
                resolved_now = []
                for num in all_unresolved:
                    if "duong_kinh_ngoai" not in specs_in_ctx and 150 <= num <= 500:
                        specs_in_ctx["duong_kinh_ngoai"] = {
                            "value": float(num),
                            "uom": "mm",
                            "spec_name": _("Đường kính ngoài")
                        }
                        resolved_now.append(num)
                    elif "rang" not in specs_in_ctx and num == int(num) and 8 <= num <= 30:
                        specs_in_ctx["rang"] = {
                            "value": int(num),
                            "uom": "răng",
                            "spec_name": _("Số răng")
                        }
                        resolved_now.append(num)
                all_unresolved = [n for n in all_unresolved if n not in resolved_now]

        new_ctx["unresolved_numerics"] = all_unresolved
        new_ctx["specs"] = specs_in_ctx

        # Cập nhật sản phẩm ngữ cảnh nếu router tìm thấy sản phẩm cơ sở
        target_prod = route_res.get("target_product")
        if target_prod:
            new_ctx["active_product_id"] = target_prod.id
            new_ctx["active_product_name"] = target_prod.display_name
            new_ctx["active_product_code"] = target_prod.default_code
            if target_prod.categ_id:
                new_ctx["active_category_id"] = target_prod.categ_id.id
                new_ctx["active_category_name"] = target_prod.categ_id.complete_name
        elif self.context_product_id:
            new_ctx["active_product_id"] = self.context_product_id.id
            new_ctx["active_product_name"] = self.context_product_id.display_name
            new_ctx["active_product_code"] = self.context_product_id.default_code

        # Nếu chưa có active_product_id nhưng người dùng hỏi thay thế hoặc so sánh,
        # kế thừa sản phẩm từ kết quả tìm kiếm của tin nhắn trước
        is_replacement_req = bool(re.search(r'\b(thay\s+thế|thay\s+cho|tương\s+đương|lắp\s+vừa)\b', q_lower))
        if not new_ctx.get("active_product_id") and (is_replacement_req or is_compare):
            last_msgs = self.message_ids.filtered(lambda m: m.role == "assistant").sorted("id", reverse=True)
            for m in last_msgs:
                if m.matched_product_ids:
                    p = m.matched_product_ids[0]
                    new_ctx["active_product_id"] = p.id
                    new_ctx["active_product_name"] = p.display_name
                    new_ctx["active_product_code"] = p.default_code
                    if p.categ_id:
                        new_ctx["active_category_id"] = p.categ_id.id
                        new_ctx["active_category_name"] = p.categ_id.complete_name
                    break

        # Bối cảnh xe/động cơ
        eq_terms = route_res.get("equipment_terms") or []
        if eq_terms:
            existing_eq = new_ctx.get("equipment_terms") or []
            new_ctx["equipment_terms"] = list(set(existing_eq + eq_terms))

        return new_ctx

    # =========================================================================
    # CONVERSATIONAL SEARCH PIPELINE & SPEC MATCHING
    # =========================================================================

    def _execute_conversational_search(self, ctx, raw_query):
        """Thực thi tìm kiếm phụ tùng toàn diện dựa trên ngữ cảnh nhiều lượt hợp nhất.
        Ưu tiên:
        1. Tìm kiếm thay thế kỹ thuật (Matching Engine) nếu có sản phẩm cơ sở hoặc yêu cầu thay thế/thông số.
        2. Tìm kiếm chính xác SKU nếu người dùng nhập mã.
        3. Tìm kiếm theo thông số kỹ thuật tích lũy.
        4. Tìm kiếm theo bối cảnh xe/động cơ hoặc tên phụ tùng.
        """
        engine = self.env["qba.spec.matching.engine"]
        assistant_helper = self.env["qba.ai.assistant"]
        q_lower = raw_query.lower()

        # Kiểm tra ý định tìm phụ tùng thay thế (Explicit Replacement Search)
        is_replacement_req = bool(re.search(r'\b(thay\s+thế|thay\s+cho|tương\s+đương|lắp\s+vừa)\b', q_lower))
        active_prod_id = ctx.get("active_product_id")
        active_cat_id = ctx.get("active_category_id")
        active_specs = ctx.get("specs") or {}

        # Kịch bản 1: Yêu cầu tìm phụ tùng thay thế hoặc so sánh cho sản phẩm cơ sở
        if (is_replacement_req or ctx.get("mode") in ("replacement", "compare")) and active_prod_id:
            prod = self.env["product.template"].browse(active_prod_id).exists()
            if prod:
                # Gọi hàm _generate_matching_explanation từ ai_assistant model để tái sử dụng toàn vẹn logic
                matching_html, extra_prods, timings = assistant_helper._generate_matching_explanation(
                    raw_query, self.env["product.template"].browse([prod.id])
                )
                candidates = extra_prods or self.env["product.template"].browse()
                return {
                    "mode": ctx.get("mode") if ctx.get("mode") == "compare" else "replacement",
                    "base_product": prod,
                    "products": candidates,
                    "matching_explanation_html": matching_html,
                    "timings": timings,
                }

        # Kịch bản 2: Có thông số kỹ thuật tích lũy (ví dụ: phi 325, thêm 10 răng, thêm 8 lò xo)
        if active_specs:
            cat_id = active_cat_id
            if not cat_id and active_prod_id:
                p = self.env["product.template"].browse(active_prod_id)
                cat_id = p.categ_id.id if p.exists() else False

            # Tự động suy luận danh mục từ các spec definition nếu chưa có
            if not cat_id:
                spec_codes = list(active_specs.keys())
                defs = self.env['qba.product.spec.definition'].search([('code', 'in', spec_codes)])
                cand_cats = defs.mapped('category_ids')
                if len(cand_cats) == 1:
                    cat_id = cand_cats[0].id
                elif len(cand_cats) > 1:
                    cat_counts = {}
                    for d in defs:
                        for c in d.category_ids:
                            cat_counts[c.id] = cat_counts.get(c.id, 0) + 1
                    cat_id = max(cat_counts, key=cat_counts.get)

            found_prods = self.env["product.template"].browse()
            explanation_html = ""
            timings = None
            brand_filter = ctx.get("brand")

            if cat_id:
                try:
                    matching_res = engine.find_matching_products(cat_id, active_specs, options={"limit": 10})
                    if matching_res.get("success"):
                        explanation_html = matching_res.get("explanation_html") or ""
                        timings = matching_res.get("timing")
                        ranked = matching_res.get("ranked_matches", [])
                        cand_ids = [m["candidate_id"] for m in ranked if m.get("candidate_id")]
                        if not cand_ids:
                            # Lấy các ứng viên thỏa mãn toàn bộ thông số đầu vào mà không vi phạm hard constraint
                            insufficient = matching_res.get("insufficient_candidates", [])
                            cand_ids = []
                            for m in insufficient:
                                if not m.get("candidate_id") or m.get("violated_hard_constraints") or m.get("has_violation"):
                                    continue
                                comp_lines = {l.get("spec_code"): l for l in m.get("comparison_lines", [])}
                                all_user_specs_matched = True
                                for s_code in active_specs:
                                    line = comp_lines.get(s_code)
                                    if not line or line.get("line_status") not in ("exact_match", "partial_match"):
                                        all_user_specs_matched = False
                                        break
                                if all_user_specs_matched:
                                    cand_ids.append(m["candidate_id"])
                        found_prods = self.env["product.template"].browse(cand_ids)
                except Exception as e:
                    _logger.warning("Lỗi khi chạy matching engine từ specs tích lũy: %s", e)

            # Nếu Matching Engine không trả về ứng viên nào, tìm kiếm trực tiếp trên EAV
            if not found_prods:
                eav_prods, diagnostic_info = self._search_products_by_specs_eav(
                    active_specs, category_id=cat_id, brand_filter=brand_filter
                )
                found_prods = eav_prods
            else:
                _, diagnostic_info = self._search_products_by_specs_eav(
                    active_specs, category_id=cat_id, brand_filter=brand_filter
                )

            # Áp dụng bộ lọc thương hiệu nếu có
            if brand_filter and found_prods:
                filtered_by_brand = found_prods.filtered(
                    lambda p: brand_filter.lower() in (p.brand_id.name or "").lower() or brand_filter.lower() in (p.name or "").lower()
                )
                if filtered_by_brand:
                    found_prods = filtered_by_brand

            return {
                "mode": "specs",
                "products": found_prods,
                "matching_explanation_html": explanation_html,
                "timings": timings,
                "specs_used": active_specs,
                "diagnostic_info": diagnostic_info,
            }

        # Kịch bản 3: Tìm kiếm theo mã SKU hoặc tên phụ tùng / bối cảnh xe
        found_prods = assistant_helper._search_products(raw_query)
        # Áp dụng bộ lọc thương hiệu nếu có
        brand_filter = ctx.get("brand")
        if brand_filter and found_prods:
            filtered_by_brand = found_prods.filtered(
                lambda p: brand_filter.lower() in (p.brand_id.name or "").lower() or brand_filter.lower() in (p.name or "").lower()
            )
            if filtered_by_brand:
                found_prods = filtered_by_brand

        # Tạo giải thích matching nhẹ nhàng cho tìm kiếm danh mục/kho
        matching_banner = ""
        if found_prods:
            matching_banner = (
                f"<div class='alert alert-light border p-2 small text-muted'>"
                f"  <i class='fa fa-search me-1'></i>Tìm thấy <b>{len(found_prods)}</b> sản phẩm phù hợp với từ khóa và bộ lọc."
                f"</div>"
            )

        return {
            "mode": "general_search",
            "products": found_prods,
            "matching_explanation_html": matching_banner,
        }

    def _search_products_by_specs_eav(self, specs, category_id=None, brand_filter=None):
        """Tìm kiếm sản phẩm trực tiếp từ bảng EAV (qba.product.spec.value) thỏa mãn tất cả thông số.
        Đồng thời tính toán số lượng từng thông số riêng lẻ (Diagnostic Spec Breakdown)
        để phục vụ báo cáo giải thích khi không tìm thấy kết quả.
        """
        if not specs:
            return self.env["product.template"].browse(), {}

        spec_val_model = self.env["qba.product.spec.value"]
        prod_model = self.env["product.template"]

        individual_counts = {}
        unverified_counts = {}
        spec_product_sets = []

        base_prod_domain = [("active", "=", True)]
        if category_id:
            base_prod_domain.append(("categ_id", "child_of", category_id))
        all_eligible_prods = prod_model.search(base_prod_domain)
        all_eligible_ids = set(all_eligible_prods.ids)

        for code, spec_data in specs.items():
            val = spec_data.get("value")
            if val is None:
                continue

            all_vals = spec_val_model.search([
                ("spec_code", "=", code),
                ("product_tmpl_id", "in", list(all_eligible_ids)),
            ])

            def _val_match(v):
                if isinstance(val, (int, float)):
                    if v.value_integer and v.value_integer == int(val):
                        return True
                    if v.value_float and abs(v.value_float - float(val)) < 0.05:
                        return True
                    if v.value_display and str(int(val) if val == int(val) else val) in v.value_display:
                        return True
                    return False
                else:
                    return str(val).lower().strip() in (v.value_display or "").lower().strip()

            matching_vals = all_vals.filtered(_val_match)

            # Đếm số lượng sản phẩm đã xác thực (verified)
            verified_vals = matching_vals.filtered(lambda v: v.validation_status == "verified")
            verified_prod_ids = set(verified_vals.mapped("product_tmpl_id.id"))
            individual_counts[code] = len(verified_prod_ids)
            spec_product_sets.append(verified_prod_ids)

            # Đếm số lượng sản phẩm unverified / conflicted
            unverified_vals = matching_vals.filtered(lambda v: v.validation_status != "verified")
            unverified_prod_ids = set(unverified_vals.mapped("product_tmpl_id.id"))
            unverified_counts[code] = len(unverified_prod_ids)

        if spec_product_sets:
            intersected_ids = set.intersection(*spec_product_sets)
        else:
            intersected_ids = set()

        matched_prods = prod_model.browse(list(intersected_ids))
        if brand_filter and matched_prods:
            matched_prods = matched_prods.filtered(
                lambda p: brand_filter.lower() in (p.brand_id.name or "").lower() or brand_filter.lower() in (p.name or "").lower()
            )

        diagnostic_info = {
            "individual_counts": individual_counts,
            "unverified_counts": unverified_counts,
            "eliminated_by": [code for code, cnt in individual_counts.items() if cnt == 0],
        }

        return matched_prods, diagnostic_info

    # =========================================================================
    # PRODUCT CARDS FORMATTER (PRODUCT-CENTERED CHAT RESULTS)
    # =========================================================================

    def _build_product_cards(self, products, ctx):
        """Xây dựng dữ liệu thẻ sản phẩm có cấu trúc chuẩn để hiển thị trực quan trong giao diện chat."""
        cards = []
        user = self.env.user
        can_see_price = user.has_group("sales_team.group_sale_salesman") or user.has_group("base.group_user")
        can_see_stock = user.has_group("stock.group_stock_user")

        for p in products[:10]:
            # Đọc các thông số kỹ thuật đã duyệt (Verified Specs) của sản phẩm
            verified_specs = []
            for val in p.spec_value_ids.filtered(lambda v: v.validation_status == "verified" and v.spec_definition_id.active):
                verified_specs.append({
                    "code": val.spec_code,
                    "name": val.spec_definition_id.name,
                    "value": val.value_display,
                    "uom": val.uom or "",
                    "is_critical": val.is_critical,
                })

            card = {
                "id": p.id,
                "name": p.name,
                "default_code": p.default_code or "N/A",
                "category_id": p.categ_id.id if p.categ_id else False,
                "category_name": p.categ_id.display_name or _("Chưa phân loại"),
                "brand_name": p.brand_id.name if hasattr(p, "brand_id") and p.brand_id else "",
                "price": f"{p.list_price:,.0f} ₫" if can_see_price and p.list_price else "",
                "verified_specs": verified_specs[:4],  # Hiển thị 4 thông số tiêu biểu
                "verified_count": len(verified_specs),
                "actions": [
                    {"type": "open_product", "label": _("Xem chi tiết"), "icon": "fa-external-link"},
                    {"type": "find_substitutes", "label": _("Tìm thay thế"), "icon": "fa-exchange"},
                ]
            }
            cards.append(card)

        return cards

    # =========================================================================
    # CONVERSATIONAL RESPONSE SYNTHESIS (GEMINI OR DETERMINISTIC FALLBACK)
    # =========================================================================

    def _synthesize_conversational_response(self, query, intent, merged_ctx, search_results, product_cards):
        """Tổng hợp câu trả lời đàm thoại ngắn gọn, chuyên nghiệp và có tính hỗ trợ cao:
        1. Ưu tiên giải thích tự nhiên, chính xác, nêu bật các điều kiện đang áp dụng.
        2. Nếu Gemini khả dụng và câu hỏi cần đàm thoại -> gọi Gemini hỗ trợ tổng hợp lời thoại.
        3. Nếu Gemini bị lỗi quota/rate-limit -> lập tức fallback sang phản hồi xác thực dựa trên dữ liệu thật (Không bịa đặt).
        """
        mode = search_results.get("mode")
        prod_count = len(product_cards)
        specs_used = merged_ctx.get("specs") or {}
        brand_used = merged_ctx.get("brand")

        # Chuẩn bị tóm tắt các điều kiện lọc đang có hiệu lực
        filters_summary_parts = []
        if specs_used:
            specs_str = ", ".join([f"{k}: {v.get('value')} {v.get('uom','')}" for k, v in specs_used.items()])
            filters_summary_parts.append(_("Thông số: %s") % specs_str)
        if brand_used:
            filters_summary_parts.append(_("Thương hiệu: %s") % brand_used)
        if merged_ctx.get("equipment_terms"):
            filters_summary_parts.append(_("Dòng xe/động cơ: %s") % ", ".join(merged_ctx["equipment_terms"]))

        filter_text = f" (Áp dụng điều kiện: {'; '.join(filters_summary_parts)})" if filters_summary_parts else ""

        # Kịch bản 0: Truy vấn mơ hồ hoặc yêu cầu làm rõ từ router
        if mode == "ambiguous" or intent == "ambiguous" or search_results.get("clarification"):
            clarif = search_results.get("clarification") or merged_ctx.get("clarification_message")
            if clarif:
                return clarif

        # Kịch bản A: Tìm kiếm phụ tùng thay thế (Replacement Mode)
        if mode == "replacement":
            base_p = search_results.get("base_product")
            base_name = f"{base_p.name} [{base_p.default_code or 'N/A'}]" if base_p else _("Sản phẩm cơ sở")
            if prod_count > 0:
                return (
                    f"Tôi đã đối chiếu thông số kỹ thuật đã duyệt và tìm thấy **{prod_count} sản phẩm** có khả năng thay thế tương đương cho **{base_name}** trong kho QBA.\n\n"
                    f"Bạn có thể xem các gợi ý phù hợp nhất ở bên dưới, hoặc bấm vào nút **'Xem chi tiết'** trên từng sản phẩm."
                )
            else:
                return (
                    f"Tôi đã quét toàn bộ danh mục để tìm phụ tùng thay thế tương đương cho **{base_name}**, "
                    f"tuy nhiên hiện tại **chưa có sản phẩm nào thỏa mãn đầy đủ các ràng buộc kích thước lắp ráp** an toàn trong kho.\n\n"
                    f"Bạn có thể xem chi tiết lý do từ chối tương thích tại bảng đối chiếu kỹ thuật bên dưới."
                )

        # Kịch bản A2: So sánh sản phẩm (Compare Mode)
        if mode == "compare":
            base_p = search_results.get("base_product")
            base_name = f"{base_p.name} [{base_p.default_code or 'N/A'}]" if base_p else _("Sản phẩm cơ sở")
            if prod_count > 0:
                return (
                    f"Dưới đây là bảng đối chiếu kỹ thuật chi tiết giữa **{base_name}** và các sản phẩm tương thích trong danh mục.\n\n"
                    f"Bạn có thể xem chi tiết từng tiêu chí kỹ thuật và thông số lắp ráp ở bảng đối chiếu bên dưới."
                )
            else:
                return (
                    f"Dưới đây là bảng đối chiếu kỹ thuật chi tiết cho sản phẩm **{base_name}**.\n\n"
                    f"Hệ thống đã phân tích các thông số kỹ thuật đã duyệt và so sánh với các sản phẩm cùng nhóm. "
                    f"Chi tiết dung sai, mức độ tương thích hoặc nguyên nhân loại trừ được hiển thị đầy đủ trong bảng đối chiếu bên dưới."
                )

        # Kịch bản B: Tìm kiếm theo thông số kỹ thuật (Specs Mode)
        if mode == "specs":
            if prod_count > 0:
                return (
                    f"Đã tìm thấy **{prod_count} sản phẩm** trong kho QBA thỏa mãn các thông số bạn yêu cầu{filter_text}.\n\n"
                    f"Dưới đây là danh sách sản phẩm phù hợp. Bạn có thể tiếp tục thêm điều kiện (ví dụ: *'chỉ lấy hàng Antek'* hoặc *'so sánh với sản phẩm khác'*)."
                )
            else:
                diag = search_results.get("diagnostic_info") or {}
                indiv = diag.get("individual_counts") or {}
                unverified = diag.get("unverified_counts") or {}
                eliminated = diag.get("eliminated_by") or []

                lines = [
                    f"Rất tiếc, kho QBA hiện **chưa có sản phẩm nào khớp đồng thời tất cả các thông số kỹ thuật**{filter_text}.\n",
                    "**Chi tiết phân tích từng điều kiện kỹ thuật trong kho:**"
                ]

                for code, spec_data in specs_used.items():
                    val = spec_data.get("value")
                    uom = spec_data.get("uom", "")
                    name = spec_data.get("spec_name", code)
                    cnt = indiv.get(code, 0)
                    unv_cnt = unverified.get(code, 0)
                    extra = f" (có {unv_cnt} sản phẩm chưa duyệt)" if unv_cnt else ""
                    if cnt > 0:
                        lines.append(f"- **{name}** = `{val} {uom}`: Tìm thấy **{cnt}** sản phẩm thỏa mãn{extra}.")
                    else:
                        lines.append(f"- **{name}** = `{val} {uom}`: **0** sản phẩm thỏa mãn ❌{extra} *(Điều kiện loại trừ)*.")

                if eliminated:
                    lines.append(f"\n👉 **Nguyên nhân chính:** Không có sản phẩm nào trong kho có thông số `{', '.join(eliminated)}` thỏa mãn.")
                else:
                    lines.append("\n👉 **Nguyên nhân:** Từng thông số riêng lẻ đều có sản phẩm thỏa mãn, nhưng **chưa có sản phẩm nào thỏa mãn đồng thời** toàn bộ tổ hợp thông số này.")

                lines.append("\n**Gợi ý:** Bạn có thể thử nới rộng dung sai hoặc bỏ bớt một thông số để mở rộng phạm vi tìm kiếm.")
                return "\n".join(lines)

        # Kịch bản C: Tìm kiếm thông thường (General Search Mode)
        if prod_count > 0:
            return (
                f"Tìm thấy **{prod_count} sản phẩm** phù hợp với yêu cầu *'{query}'*{filter_text}.\n\n"
                f"Mời bạn tham khảo danh sách phụ tùng bên dưới. Nếu cần tìm phụ tùng thay thế tương đương, hãy nhấn nút **'Tìm thay thế'** trên sản phẩm tương ứng."
            )
        else:
            return (
                f"Không tìm thấy phụ tùng nào khớp với từ khóa *'{query}'*{filter_text} trong kho QBA.\n\n"
                f"**Gợi ý tìm kiếm:**\n"
                f"- Nhập mã SKU phụ tùng (Ví dụ: `LC.002`, `TBUA.001`, `BI.087`).\n"
                f"- Nhập tên phụ tùng kèm kích thước (Ví dụ: *'Lá côn phi 325 10 răng'*, *'Bi moay ơ sau'*).\n"
                f"- Nhập tên phụ tùng kèm dòng xe (Ví dụ: *'Bánh răng Howo WP10'*)."
            )

    def _send_initial_greeting(self):
        """Tin nhắn chào mừng ban đầu khi mở phiên hội thoại mới."""
        greeting = (
            "Xin chào! Tôi là **QBA AI Assistant** — Trợ lý tìm kiếm phụ tùng xe tải thông minh.\n\n"
            "Tôi có thể giúp bạn:\n"
            "- Tìm phụ tùng theo thông số (Ví dụ: *'Tìm lá côn phi 325, 10 răng, 8 lò xo'*).\n"
            "- Tìm phụ tùng thay thế tương đương (Ví dụ: *'Tìm phụ tùng thay thế cho LC.002'*).\n"
            "- Tra cứu theo bối cảnh xe / động cơ (Ví dụ: *'Bánh răng bơm hơi Howo WP10'*).\n"
            "- Nhận diện và bổ sung thêm điều kiện lọc liên tục trong cuộc trò chuyện."
        )
        if self.context_product_id:
            greeting += (
                f"\n\nĐang làm việc trên ngữ cảnh sản phẩm: **{self.context_product_id.name}** "
                f"[Mã: `{self.context_product_id.default_code or 'N/A'}`]."
            )

        self.env["qba.ai.message"].create({
            "conversation_id": self.id,
            "user_id": self.env.user.id,
            "role": "assistant",
            "message_type": "greeting",
            "content": greeting,
        })
