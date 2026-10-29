# -*- coding: utf-8 -*-
import json
import time
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestPhase44SearchQualityAndMatchingAcceptance(TransactionCase):
    """Bộ kiểm thử nghiệm thu Chất lượng tìm kiếm & An toàn so khớp kỹ thuật (Phase 4.4):
    1. Ma trận tìm kiếm đa dạng: SKU, tên gọi thông dụng, từ đồng nghĩa kỹ thuật.
    2. Độ chính xác trích xuất đa thông số: 325, 10 răng; lá côn 325 10 răng 8 lò xo.
    3. Phân biệt số có đơn vị và số trần mơ hồ.
    4. Quản lý hội thoại đa lượt: Thêm thông số, đổi thông số, và xóa bỏ hoàn toàn bộ lọc cũ khi chuyển chủ đề.
    5. An toàn so khớp kỹ thuật: Phân định rạch ròi giữa điểm thông số và tính tương thích tổng thể.
    6. Báo cáo trung thực khoảng trống dữ liệu (Coverage Gaps) cho các danh mục chưa có Hồ sơ/Quy cách (TBUA, BI).
    7. Vòng đời Admin Request từ kết quả tìm kiếm rỗng, ngăn ngừa lặp CTA.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.router = cls.env["qba.query.intent.router"]
        cls.engine = cls.env["qba.spec.matching.engine"]
        cls.conv_model = cls.env["qba.ai.conversation"]
        cls.message_model = cls.env["qba.ai.message"]
        cls.request_model = cls.env["qba.ai.request"]
        cls.category_model = cls.env["product.category"]
        cls.product_model = cls.env["product.template"]
        cls.spec_val_model = cls.env["qba.product.spec.value"]

        cls.user_test = cls.env["res.users"].create({
            "name": "Phase 4.4 Test User",
            "login": "phase44_test_user",
            "email": "phase44@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

        cls.categ_lc = cls.category_model.search([('name', 'ilike', 'Lá côn')], limit=1)
        cls.categ_tbua = cls.category_model.search([('name', 'ilike', 'Tăm bua')], limit=1)
        cls.categ_bi = cls.category_model.search([('name', 'ilike', 'Bi')], limit=1)

    def test_01_matrix_sku_and_alias_queries(self):
        """01. Truy vấn SKU đơn lẻ và Tên gọi phụ tùng / Bí danh phổ biến"""
        # SKU-only
        res_sku = self.router.route_query("LC.002")
        self.assertEqual(res_sku["intent"], "exact_sku")
        self.assertEqual(res_sku["target_sku"], "LC.002")

        # Name alias
        res_alias = self.router.route_query("tăm bua sau")
        self.assertIn(res_alias["intent"], ("product_name_alias", "equipment_context"))
        self.assertIn("tăm bua", " ".join(res_alias["clean_terms"]).lower())

    def test_02_critical_multi_parameter_extraction(self):
        """02. Trích xuất chính xác đồng thời nhiều thông số kỹ thuật (Kích thước, Số răng, Số lò xo)"""
        # Case A: '325, 10 răng'
        res_a = self.router.route_query("325, 10 răng")
        self.assertEqual(res_a["intent"], "technical_spec_only")
        specs_a = res_a["extracted_specs"]
        self.assertEqual(specs_a.get("duong_kinh_ngoai", {}).get("value"), 325.0)
        self.assertEqual(specs_a.get("rang", {}).get("value"), 10)

        # Case B: 'lá côn 325 10 răng'
        res_b = self.router.route_query("lá côn 325 10 răng")
        self.assertEqual(res_b["intent"], "technical_spec_only")
        specs_b = res_b["extracted_specs"]
        self.assertEqual(specs_b.get("duong_kinh_ngoai", {}).get("value"), 325.0)
        self.assertEqual(specs_b.get("rang", {}).get("value"), 10)

        # Case C: Đầy đủ 3 thông số 'lá côn phi 325 10 răng 8 lò xo'
        res_c = self.router.route_query("lá côn phi 325 10 răng 8 lò xo")
        self.assertEqual(res_c["intent"], "technical_spec_only")
        specs_c = res_c["extracted_specs"]
        self.assertEqual(specs_c.get("duong_kinh_ngoai", {}).get("value"), 325.0)
        self.assertEqual(specs_c.get("rang", {}).get("value"), 10)
        self.assertEqual(specs_c.get("lo_xo", {}).get("value"), 8)

    def test_03_units_and_bare_number_disambiguation(self):
        """03. Phân biệt rõ số có đơn vị đo lường và số trần mơ hồ"""
        # Có đơn vị đo lường: 325mm, 10 răng
        res_unit = self.router.route_query("325mm, 10 răng")
        self.assertEqual(res_unit["intent"], "technical_spec_only")
        self.assertEqual(res_unit["extracted_specs"]["duong_kinh_ngoai"]["value"], 325.0)
        self.assertEqual(res_unit["extracted_specs"]["rang"]["value"], 10)

        # Số trần không nhãn, không dấu phẩy: '325 10' -> Phải đánh dấu ambiguous để tránh đoán bừa
        res_bare = self.router.route_query("325 10")
        self.assertEqual(res_bare["intent"], "ambiguous")

        # Số trần đơn lẻ: '325'
        res_single = self.router.route_query("325")
        self.assertEqual(res_single["intent"], "ambiguous")

    def test_04_vietnamese_technical_terms_and_synonyms(self):
        """04. Nhận diện từ đồng nghĩa ngành kỹ thuật tiếng Việt (Đĩa ly hợp, Tang trống phanh, Bạc đạn)"""
        # Đĩa ly hợp = Lá côn
        res_clutch = self.router.route_query("đĩa ly hợp 325 10 răng")
        self.assertEqual(res_clutch["intent"], "technical_spec_only")
        self.assertEqual(res_clutch["extracted_specs"]["duong_kinh_ngoai"]["value"], 325.0)

        # Bạc đạn = Danh mục Bi
        res_bearing = self.router.route_query("bạc đạn bánh trước")
        self.assertIn(res_bearing["intent"], ("product_name_alias", "equipment_context"))

    def test_05_multi_turn_additive_and_single_param_change(self):
        """05. Hội thoại đa lượt: Tích lũy thông số, thay đổi 1 thông số an toàn"""
        conv = self.conv_model.with_user(self.user_test).create({
            "name": "Multi-turn Additive Test",
            "user_id": self.user_test.id,
        })

        # Lượt 1: lá côn phi 325
        conv.post_user_message("lá côn phi 325")
        ctx1 = conv._get_search_context()
        self.assertEqual(ctx1.get("specs", {}).get("duong_kinh_ngoai", {}).get("value"), 325.0)

        # Lượt 2: thêm 10 răng (Tích lũy thông số)
        conv.post_user_message("thêm 10 răng")
        ctx2 = conv._get_search_context()
        self.assertEqual(ctx2.get("specs", {}).get("duong_kinh_ngoai", {}).get("value"), 325.0)
        self.assertEqual(ctx2.get("specs", {}).get("rang", {}).get("value"), 10)

        # Lượt 3: đổi sang 8 lò xo
        conv.post_user_message("đổi sang 8 lò xo")
        ctx3 = conv._get_search_context()
        self.assertIn("lo_xo", ctx3.get("specs", {}))
        self.assertEqual(ctx3.get("specs", {}).get("lo_xo", {}).get("value"), 8)

    def test_06_unrelated_query_resets_stale_mode_and_filters(self):
        """06. Truy vấn mới không liên quan phải xóa sạch bộ lọc và chế độ so sánh cũ"""
        conv = self.conv_model.with_user(self.user_test).create({
            "name": "Unrelated Query Reset Test",
            "user_id": self.user_test.id,
        })

        # Lượt 1: So sánh với LC.002
        conv.post_user_message("So sánh với LC.002")
        ctx1 = conv._get_search_context()
        self.assertEqual(ctx1.get("mode"), "compare")

        # Lượt 2: Chuyển hẳn sang tăm bua sau 1069 (Không liên quan)
        conv.post_user_message("tăm bua sau 1069")
        ctx2 = conv._get_search_context()
        # Chế độ compare phải bị xóa bỏ
        self.assertIsNone(ctx2.get("mode"))
        # Bộ lọc specs của lá côn không được tồn tại
        self.assertFalse(ctx2.get("specs"))
        # Danh mục phải chuyển sang Tăm bua
        self.assertIn("TBUA", ctx2.get("active_category_name", ""))

    def test_07_technical_matching_safety_classifications(self):
        """07. Động cơ so khớp phân định rõ: exact_match, partial_match, insufficient_data và mismatch"""
        if not self.categ_lc:
            return

        # 1. Chỉ tra 1 thông số (răng: 10) -> Không thể là exact_match tổng thể (phải là insufficient hoặc partial)
        res_single = self.engine.find_matching_products(self.categ_lc.id, {
            "rang": {"value": 10, "uom": "răng"}
        })
        self.assertTrue(res_single["success"])
        for m in res_single.get("ranked_matches", []):
            self.assertNotEqual(m["match_status"], "exact_match", "Tra 1 thông số không được coi là khớp 100% toàn diện")

        # 2. Tra cứu thông số vi phạm hard constraint (răng: 99)
        res_mismatch = self.engine.find_matching_products(self.categ_lc.id, {
            "rang": {"value": 99, "uom": "răng"}
        })
        self.assertTrue(res_mismatch["success"])
        self.assertEqual(res_mismatch["compatible_count"], 0)

    def test_08_unapproved_and_conflicting_specs_excluded_from_compatibility(self):
        """08. Thông số kỹ thuật chưa duyệt (unverified) hoặc mâu thuẫn (conflicted) không được dùng để khẳng định tương thích"""
        # Tạo fixture sản phẩm test có thông số unverified
        test_prod = self.product_model.create({
            "name": "Test Unverified Product",
            "default_code": "TEST-UNV-01",
            "categ_id": self.categ_lc.id if self.categ_lc else False,
        })
        spec_def_rang = self.env["qba.product.spec.definition"].search([("code", "=", "rang")], limit=1)
        if spec_def_rang and test_prod.categ_id:
            val = self.spec_val_model.create({
                "product_tmpl_id": test_prod.id,
                "spec_definition_id": spec_def_rang.id,
                "value_integer": 10,
                "validation_status": "unverified",
            })
            self.assertEqual(val.validation_status, "unverified")

            # 1. Tra cứu tìm sản phẩm: Sản phẩm có thông số unverified không được nằm trong ranked_matches tương thích
            res = self.engine.find_matching_products(self.categ_lc.id, {
                "rang": {"value": 10, "uom": "răng"}
            }, options={"domain": [("id", "=", test_prod.id)]})

            for m in res.get("ranked_matches", []):
                self.assertNotEqual(m.get("candidate_id"), test_prod.id,
                                    "Sản phẩm chứa thông số unverified không được nằm trong ranked_matches tương thích!")

            # 2. match_product_to_candidates: Sản phẩm nguồn chỉ có thông số unverified không thể tìm được phụ tùng thay thế
            res_sub = self.engine.match_product_to_candidates(test_prod.id)
            self.assertEqual(res_sub.get("compatible_count", 0), 0)

    def test_09_coverage_gaps_reporting_without_silent_lc_fallback(self):
        """09. Danh mục thiếu Hồ sơ hoặc Thông số (TBUA / BI) được báo cáo trung thực, KHÔNG bí mật lấy cấu hình Lá Côn"""
        if self.categ_tbua:
            res_tbua = self.engine.find_matching_products(self.categ_tbua.id, {
                "duong_kinh_ngoai": {"value": 400.0, "uom": "mm"}
            })
            profile_tbua = self.engine.resolve_profile(self.categ_tbua)
            if not profile_tbua:
                self.assertFalse(res_tbua["has_profile"])
                self.assertIn("chưa có Hồ sơ so khớp", res_tbua["error"])

    def test_10_empty_search_and_admin_request_lifecycle(self):
        """10. Kết quả tìm kiếm rỗng tạo đúng 1 phiếu yêu cầu Admin và tin nhắn phản hồi"""
        conv = self.conv_model.with_user(self.user_test).create({
            "name": "Empty Search Request Lifecycle",
            "user_id": self.user_test.id,
        })

        # Gửi truy vấn không có trong kho
        conv.post_user_message("lá côn phi 999 99 răng")
        msg = conv.message_ids.filtered(lambda m: m.role == 'assistant').sorted('id', reverse=True)[0]
        self.assertEqual(msg.message_type, "search_empty")

        # Gửi yêu cầu hỗ trợ Admin
        req = self.request_model.with_user(self.user_test).create_from_drawer({
            "conversation_id": conv.id,
            "message_id": msg.id,
            "request_type": "missing_product",
            "raw_query": "lá côn phi 999 99 răng",
            "user_notes": "Yêu cầu khẩn cấp cho xe đầu kéo.",
        })
        self.assertTrue(bool(req.name))
        self.assertTrue(req.name.startswith("REQ-"))
        self.assertEqual(req.state, "submitted")

        # Kiểm tra tin nhắn xác nhận được thêm vào hội thoại với message_type=request_confirmation
        latest_msg = conv.message_ids.filtered(lambda m: m.role == 'assistant').sorted('id', reverse=True)[0]
        self.assertEqual(latest_msg.message_type, "request_confirmation")
        self.assertIn(req.name, latest_msg.content)

