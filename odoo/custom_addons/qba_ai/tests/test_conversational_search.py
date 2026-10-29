# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
import json


class TestConversationalSearch(TransactionCase):
    """Bộ kiểm thử Trợ lý Hội thoại Tìm Kiếm Phụ Tùng QBA AI"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conversation_model = cls.env["qba.ai.conversation"]
        cls.message_model = cls.env["qba.ai.message"]
        cls.product_model = cls.env["product.template"]
        cls.category_model = cls.env["product.category"]
        cls.user_model = cls.env["res.users"]

        # Tìm hoặc tạo người dùng thử nghiệm
        group_user = cls.env.ref("base.group_user")
        cls.user_a = cls.user_model.create({
            "name": "Nhân Viên Kinh Doanh A",
            "login": "sale_user_a",
            "email": "user_a@qba.vn",
            "groups_id": [(6, 0, [group_user.id])],
        })
        cls.user_b = cls.user_model.create({
            "name": "Nhân Viên Kinh Doanh B",
            "login": "sale_user_b",
            "email": "user_b@qba.vn",
            "groups_id": [(6, 0, [group_user.id])],
        })

        # Danh mục và sản phẩm mẫu
        cls.categ_lc = cls.category_model.search([('name', 'ilike', 'LC')], limit=1)
        if not cls.categ_lc:
            cls.categ_lc = cls.category_model.create({'name': 'LC - Lá Côn Ly Hợp'})

        cls.sample_product = cls.product_model.search([('categ_id', '=', cls.categ_lc.id)], limit=1)
        if not cls.sample_product:
            cls.sample_product = cls.product_model.create({
                "name": "Lá Côn Howo 371 Phi 325 10R",
                "default_code": "LC.SEARCH.TEST",
                "categ_id": cls.categ_lc.id,
            })

    def test_01_conversation_lifecycle(self):
        """Kiểm tra vòng đời hội thoại: tạo mới, lấy phiên hoạt động và lưu trữ"""
        conv = self.conversation_model.with_user(self.user_a).get_or_create_active_conversation()
        self.assertTrue(conv.exists())
        self.assertEqual(conv.user_id.id, self.user_a.id)
        self.assertEqual(conv.state, "active")

        # Gọi lại get_or_create_active_conversation phải trả về đúng conversation này
        same_conv = self.conversation_model.with_user(self.user_a).get_or_create_active_conversation()
        self.assertEqual(same_conv.id, conv.id)

        # Tạo mới hội thoại mới sẽ archive hội thoại cũ
        new_conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        self.assertNotEqual(new_conv.id, conv.id)
        self.assertEqual(conv.state, "archived")
        self.assertEqual(new_conv.state, "active")

    def test_02_multiturn_spec_accumulation(self):
        """Kiểm tra tích lũy thông số đa lượt (multi-turn context retention)"""
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()

        # Turn 1: Tìm lá côn phi 325
        res1 = conv.post_user_message("Tìm lá côn phi 325")
        self.assertTrue(res1["success"])
        search_ctx1 = conv.get_search_context()
        self.assertTrue(bool(search_ctx1.get("specs")))
        # Kiểm tra thông số đường kính có được nhận diện
        specs = search_ctx1.get("specs", {})
        has_diameter = any("325" in str(v) or k in ["phi", "diameter_outer", "duong_kinh_ngoai"] for k, v in specs.items())
        self.assertTrue(has_diameter, f"Specs {specs} phải chứa thông số phi 325")

        # Turn 2: Thêm 10 răng, 8 lò xo
        res2 = conv.post_user_message("Thêm 10 răng, 8 lò xo")
        self.assertTrue(res2["success"])
        search_ctx2 = conv.get_search_context()
        specs2 = search_ctx2.get("specs", {})
        has_teeth = any("10" in str(v) or k in ["rang", "teeth", "so_rang"] for k, v in specs2.items())
        has_springs = any("8" in str(v) or k in ["lo_xo", "springs", "so_lo_xo"] for k, v in specs2.items())
        self.assertTrue(has_teeth, f"Specs {specs2} phải tích lũy 10 răng")
        self.assertTrue(has_springs, f"Specs {specs2} phải tích lũy 8 lò xo")
        # Thông số phi 325 từ Turn 1 vẫn phải còn
        has_diameter_turn2 = any("325" in str(v) or k in ["phi", "diameter_outer", "duong_kinh_ngoai"] for k, v in specs2.items())
        self.assertTrue(has_diameter_turn2, f"Specs {specs2} phải giữ nguyên phi 325 từ lượt 1")

        # Turn 3: Lọc hãng Antek
        res3 = conv.post_user_message("Chỉ Antek")
        self.assertTrue(res3["success"])
        search_ctx3 = conv.get_search_context()
        self.assertEqual(search_ctx3.get("brand"), "Antek")
        # Specs vẫn được bảo toàn
        self.assertTrue(bool(search_ctx3.get("specs")))

    def test_03_contextual_product_and_substitutes(self):
        """Kiểm tra đặt sản phẩm ngữ cảnh và truy vấn tìm thay thế"""
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation(
            context_product_id=self.sample_product.id
        )
        self.assertEqual(conv.context_product_id.id, self.sample_product.id)

        # Hỏi tìm phụ tùng thay thế
        res = conv.post_user_message("Có phụ tùng thay thế nào tương thích không?")
        self.assertTrue(res["success"])
        last_msg = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertEqual(last_msg.role, "assistant")
        self.assertTrue(bool(last_msg.content))

        # Gỡ sản phẩm ngữ cảnh
        conv.clear_context_product()
        self.assertFalse(conv.context_product_id)

    def test_04_user_isolation_security(self):
        """Kiểm tra phân quyền: User B không thể truy cập hội thoại của User A"""
        conv_a = self.conversation_model.with_user(self.user_a).create_new_conversation()
        conv_a.post_user_message("Tin nhắn bảo mật của User A")

        # User B tìm kiếm danh sách hội thoại
        convs_b = self.conversation_model.with_user(self.user_b).search([])
        self.assertNotIn(conv_a.id, convs_b.ids, "User B không được thấy hội thoại của User A")

        # Quản trị viên (Admin) thấy được tất cả
        admin_user = self.env.ref("base.user_admin")
        convs_admin = self.conversation_model.with_user(admin_user).search([])
        self.assertIn(conv_a.id, convs_admin.ids, "Admin phải thấy được hội thoại")

    def test_05_message_serialization_to_dict(self):
        """Kiểm tra serialize dữ liệu JSON cho OWL component"""
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        conv.post_user_message("Tìm lá côn phi 325 10 răng")

        data = conv.to_dict()
        self.assertIn("conversation_id", data)
        self.assertIn("messages", data)
        self.assertIn("search_context", data)
        self.assertTrue(len(data["messages"]) >= 2)  # 1 user + 1 assistant

        assistant_msg = next(m for m in data["messages"] if m["role"] == "assistant")
        self.assertIn("matched_products", assistant_msg)
        self.assertIn("perf_info", assistant_msg)
        self.assertIn("content", assistant_msg)

    def test_06_numeric_spec_extraction_bare_numbers(self):
        """Kiểm tra câu hỏi '325, 10 răng':
        - Không được bỏ rơi số 325.
        - Tự động nhận diện '325' là đường kính ngoài và '10' là răng.
        - Trả về sản phẩm thỏa mãn (trong DB thực tế có LC.002 và LC.007).
        """
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        res = conv.post_user_message("325, 10 răng")
        self.assertTrue(res["success"])

        search_ctx = conv.get_search_context()
        specs = search_ctx.get("specs", {})
        self.assertIn("rang", specs, f"Specs {specs} phải chứa 'rang'")
        self.assertEqual(specs["rang"]["value"], 10)
        self.assertIn("duong_kinh_ngoai", specs, f"Specs {specs} phải chứa 'duong_kinh_ngoai'")
        self.assertEqual(specs["duong_kinh_ngoai"]["value"], 325.0)

        # Kiểm tra tin nhắn trả lời
        last_msg = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertEqual(last_msg.role, "assistant")
        self.assertNotIn("Không tìm thấy phụ tùng nào khớp với từ khóa", last_msg.content)
        # Kiểm tra sản phẩm tìm thấy
        matched = last_msg.matched_product_ids
        if self.env["product.template"].search([('default_code', 'in', ['LC.002', 'LC.007'])]):
            self.assertTrue(len(matched) >= 1, "Phải tìm thấy ít nhất 1 sản phẩm thỏa mãn 325, 10 răng")

    def test_07_bare_number_alone_ambiguity(self):
        """Kiểm tra truy vấn chỉ có số trần đơn độc '325' không có ngữ cảnh:
        - Router phải phân loại là ambiguous.
        - Trả lời yêu cầu người dùng làm rõ thông số hoặc danh mục.
        """
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        res = conv.post_user_message("325")
        self.assertTrue(res["success"])

        last_msg = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertEqual(last_msg.role, "assistant")
        self.assertTrue(
            "chưa rõ" in last_msg.content or "làm rõ" in last_msg.content or "bổ sung" in last_msg.content,
            f"Nội dung '{last_msg.content}' phải yêu cầu làm rõ con số 325"
        )

    def test_08_diagnostic_breakdown_on_empty_results(self):
        """Kiểm tra khi không có sản phẩm nào thỏa mãn tổ hợp thông số:
        - Báo cáo phân tích từng điều kiện trong kho.
        - Chỉ rõ thông số nào đã loại trừ kết quả.
        """
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        # Tìm lá côn 325, 10 răng, nhưng yêu cầu 99 lò xo (chắc chắn không có trong kho)
        res = conv.post_user_message("lá côn phi 325, 10 răng, 99 lò xo")
        self.assertTrue(res["success"])

        last_msg = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertEqual(last_msg.role, "assistant")
        self.assertEqual(len(last_msg.matched_product_ids), 0)
        # Kiểm tra giải thích có liệt kê chi tiết từng điều kiện
        self.assertIn("Chi tiết phân tích từng điều kiện", last_msg.content)
        self.assertIn("99", last_msg.content)

    def test_09_multiturn_chain_persistence(self):
        """Kiểm tra chuỗi hội thoại nhiều lượt:
        Turn 1: '325, 10 răng'
        Turn 2: 'Thêm 8 lò xo'
        Turn 3: 'Chỉ Antek'
        Duy trì và tích lũy đầy đủ toàn bộ điều kiện.
        """
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        # Turn 1
        conv.post_user_message("325, 10 răng")
        ctx1 = conv.get_search_context()
        self.assertEqual(len(ctx1.get("specs", {})), 2)

        # Turn 2
        conv.post_user_message("Thêm 8 lò xo")
        ctx2 = conv.get_search_context()
        self.assertEqual(len(ctx2.get("specs", {})), 3)
        self.assertIn("lo_xo", ctx2["specs"])
        self.assertEqual(ctx2["specs"]["lo_xo"]["value"], 8)

        # Turn 3
        conv.post_user_message("Chỉ Antek")
        ctx3 = conv.get_search_context()
        self.assertEqual(ctx3.get("brand"), "Antek")
        self.assertEqual(len(ctx3.get("specs", {})), 3)

        last_msg = conv.message_ids.sorted("id", reverse=True)[0]
        if self.env["product.template"].search([('default_code', '=', 'LC.002')]):
            self.assertTrue(
                any(p.default_code == "LC.002" for p in last_msg.matched_product_ids),
                "LC.002 (Antek 325-10R 8 lò xo) phải nằm trong danh sách kết quả"
            )

    def test_10_variations_outer_diameter_syntax(self):
        """Kiểm tra các biến thể cú pháp của đường kính ngoài kết hợp răng:
        - '325mm, 10 răng'
        - 'lá côn 325, 10 răng'
        - 'lá côn phi 325 10R'
        """
        variations = [
            "325mm, 10 răng",
            "lá côn 325, 10 răng",
            "lá côn phi 325 10R",
        ]
        router = self.env["qba.query.intent.router"]
        for q in variations:
            res = router.route_query(q)
            specs = res.get("extracted_specs", {})
            self.assertIn("rang", specs, f"Query '{q}' phải trích xuất được 'rang'")
            self.assertEqual(specs["rang"]["value"], 10, f"Query '{q}' phải có răng = 10")
            self.assertIn("duong_kinh_ngoai", specs, f"Query '{q}' phải trích xuất được 'duong_kinh_ngoai'")
            self.assertEqual(specs["duong_kinh_ngoai"]["value"], 325.0, f"Query '{q}' phải có duong_kinh_ngoai = 325")

    def test_11_explanation_html_separation_from_content(self):
        """Kiểm tra sự phân tách rạch ròi giữa msg.content và msg.explanation_html:
        - msg.content CHỈ chứa văn bản đàm thoại tự nhiên, không chứa HTML thô.
        - msg.explanation_html chứa mã HTML bảng đối chiếu kỹ thuật.
        - to_dict() trả về độc lập cả hai trường.
        """
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        conv.post_user_message("Tìm lá côn phi 325, 10 răng")

        last_msg = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertEqual(last_msg.role, "assistant")

        # msg.content không được chứa source HTML dạng <div hay <table
        self.assertNotIn("<div", last_msg.content)
        self.assertNotIn("<table", last_msg.content)
        self.assertNotIn("&lt;div", last_msg.content)
        self.assertNotIn("&lt;table", last_msg.content)

        # Kiểm tra serialization to_dict
        d = last_msg.to_dict()
        self.assertIn("content", d)
        self.assertIn("explanation_html", d)
        self.assertNotIn("<div", d["content"])

    def test_12_untrusted_input_sanitization(self):
        """Kiểm tra đầu vào độc hại không được đưa raw vào content hoặc explanation:
        - Ngăn chặn XSS injection trong query của người dùng.
        """
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        malicious_input = "<script>alert('XSS')</script> lá côn phi 325"
        res = conv.post_user_message(malicious_input)
        self.assertTrue(res["success"])

        last_msg = conv.message_ids.sorted("id", reverse=True)[0]
        # Nội dung phản hồi không được chứa thẻ script thô
        self.assertNotIn("<script>", last_msg.content)
        if last_msg.explanation_html:
            self.assertNotIn("<script>", last_msg.explanation_html)

    def test_13_multiturn_replacement_and_comparison_flows(self):
        """Kiểm tra toàn vẹn luồng thay thế và so sánh đa lượt:
        - Turn 1: 'Tìm lá côn phi 325'
        - Turn 2: 'Thêm 10 răng, 8 lò xo'
        - Turn 3: 'Chỉ Antek' -> Thu hẹp LC.002
        - Turn 4: 'Có phụ tùng thay thế không?' -> Nhận diện thay thế cho LC.002, giải thích từ chối
        - Turn 5: 'So sánh với LC.002' -> Nhận diện compare, có explanation_html
        """
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()

        # Turn 1
        t1 = conv.post_user_message("Tìm lá côn phi 325")
        m1 = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertTrue(any(p.default_code == "LC.002" for p in m1.matched_product_ids))

        # Turn 2
        t2 = conv.post_user_message("Thêm 10 răng, 8 lò xo")
        m2 = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertTrue(any(p.default_code == "LC.002" for p in m2.matched_product_ids))

        # Turn 3
        t3 = conv.post_user_message("Chỉ Antek")
        m3 = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertEqual(len(m3.matched_product_ids), 1)
        self.assertEqual(m3.matched_product_ids[0].default_code, "LC.002")

        # Turn 4
        t4 = conv.post_user_message("Có phụ tùng thay thế không?")
        m4 = conv.message_ids.sorted("id", reverse=True)[0]
        self.assertEqual(m4.intent, "explicit_replacement")
        # Phản hồi không khẳng định tương thích khi thiếu dữ liệu (insufficient_data)
        self.assertIn("chưa có sản phẩm nào", m4.content)

        # Turn 5
        t5 = conv.post_user_message("So sánh với LC.002")
        m5 = conv.message_ids.sorted("id", reverse=True)[0]
        # Bảng đối chiếu kỹ thuật phải có dữ liệu HTML với đầy đủ thông số gốc và phân loại ứng viên
        self.assertTrue(m5.explanation_html)
        self.assertIn("Sản phẩm cơ sở", m5.explanation_html)
        self.assertIn("Nhóm Chưa Đủ Dữ Liệu Xác Thực", m5.explanation_html)
        self.assertNotIn("<div", m5.content)

    def test_14_conversation_history_retrieval_and_switching(self):
        """Kiểm tra chức năng xem danh sách lịch sử hội thoại cũ và chuyển đổi phiên:
        - get_user_conversations_history() trả về danh sách hội thoại của user.
        - action_open_in_drawer() kích hoạt phiên và trả về client action.
        - get_or_create_active_conversation() hỗ trợ nạp lại theo conversation_id.
        """
        # Tạo phiên 1
        conv1 = self.conversation_model.with_user(self.user_a).create_new_conversation()
        conv1.post_user_message("Tìm lá côn phi 325")

        # Tạo phiên 2 (làm conv1 chuyển sang archived)
        conv2 = self.conversation_model.with_user(self.user_a).create_new_conversation()
        conv2.post_user_message("Tìm tăm bua 10 lỗ")

        # Lấy lịch sử hội thoại
        history = self.conversation_model.with_user(self.user_a).get_user_conversations_history(limit=10)
        self.assertTrue(len(history) >= 2)
        history_ids = [h["id"] for h in history]
        self.assertIn(conv1.id, history_ids)
        self.assertIn(conv2.id, history_ids)

        # Chuyển đổi quay lại phiên 1 qua action_open_in_drawer
        action = conv1.action_open_in_drawer()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "qba_ai_assistant_open")
        self.assertEqual(action["params"]["conversation_id"], conv1.id)
        self.assertTrue(conv1.is_active)
        self.assertFalse(conv2.is_active)

        # Nạp lại phiên 1 qua get_or_create_active_conversation với conversation_id
        reloaded = self.conversation_model.with_user(self.user_a).get_or_create_active_conversation(conversation_id=conv1.id)
        self.assertEqual(reloaded.id, conv1.id)

    def test_15_conversation_deletion_and_cascade(self):
        """Kiểm tra chức năng xóa hội thoại:
        - Xóa hội thoại thành công qua ORM / action_delete.
        - Cascade tự động xóa toàn bộ tin nhắn liên quan (qba.ai.message).
        - Bảo mật: User khác không thể xóa hội thoại của người dùng (AccessError).
        """
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        conv.post_user_message("Câu hỏi test xóa 1")
        conv.post_user_message("Câu hỏi test xóa 2")

        conv_id = conv.id
        msg_ids = conv.message_ids.ids
        self.assertTrue(len(msg_ids) >= 2)

        # Kiểm tra bảo mật: user_b cố xóa conv của user_a -> AccessError
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.conversation_model.with_user(self.user_b).browse(conv_id).unlink()

        # user_a xóa hội thoại của chính mình
        res = conv.with_user(self.user_a).action_delete()
        self.assertEqual(res["type"], "ir.actions.client")

        # Xác nhận conversation không còn tồn tại
        self.assertFalse(self.conversation_model.browse(conv_id).exists())

        # Xác nhận các tin nhắn liên quan cũng bị xóa hoàn toàn theo cascade
        remaining_messages = self.message_model.sudo().search([("id", "in", msg_ids)])
        self.assertEqual(len(remaining_messages), 0)


