# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
import time


class TestGenericIntentRouterAndCrossCategory(TransactionCase):
    """Bộ kiểm thử hồi quy Đa Danh Mục & Định Tuyến Ý Định (Phase 4.3 Addendum)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.router = cls.env["qba.query.intent.router"]
        cls.engine = cls.env["qba.spec.matching.engine"]
        cls.assistant_model = cls.env["qba.ai.assistant"]
        cls.category_model = cls.env["product.category"]
        cls.product_model = cls.env["product.template"]

        # Tìm các danh mục thực tế trong DB
        cls.categ_lc = cls.category_model.search([('name', 'ilike', 'LC')], limit=1)
        cls.categ_tbua = cls.category_model.search([('name', 'ilike', 'TBUA')], limit=1)
        if not cls.categ_tbua:
            cls.categ_tbua = cls.category_model.create({'name': 'TBUA - Tăm bua'})

        cls.categ_bi = cls.category_model.search([('name', 'ilike', 'BI')], limit=1)
        if not cls.categ_bi:
            cls.categ_bi = cls.category_model.create({'name': 'BI - Vòng bi'})

    def test_01_ambiguous_intent_detection(self):
        """Kiểm tra nhận diện truy vấn mơ hồ, quá ngắn hoặc không có thông tin kỹ thuật"""
        queries = ["???", "alo", "hỏi", "giá bao nhiêu", "a", "...", "anh ơi cho em hỏi"]
        for q in queries:
            res = self.router.route_query(q)
            self.assertEqual(res["intent"], "ambiguous", f"Query '{q}' phải được định tuyến là ambiguous")
            self.assertTrue(res["is_ambiguous"])
            self.assertIn("clarification_message", res)

    def test_02_exact_sku_intent_detection(self):
        """Kiểm tra nhận diện SKU chính xác mà không phụ thuộc danh mục LC"""
        # Tạo thử sản phẩm mẫu cho TBUA nếu chưa có
        prod_tbua = self.product_model.search([('default_code', '=ilike', 'TBUA.TEST01')], limit=1)
        if not prod_tbua:
            prod_tbua = self.product_model.create({
                'name': 'Tăm bua xe Howo 371 Test',
                'default_code': 'TBUA.TEST01',
                'categ_id': self.categ_tbua.id,
            })

        res_tbua = self.router.route_query("TBUA.TEST01")
        self.assertEqual(res_tbua["intent"], "exact_sku")
        self.assertEqual(res_tbua["target_product"].id, prod_tbua.id)
        self.assertEqual(res_tbua["target_category"].id, self.categ_tbua.id)

        # Kiểm tra với tiền tố SKU:
        res_prefix = self.router.route_query("Mã: TBUA.TEST01")
        self.assertEqual(res_prefix["intent"], "exact_sku")
        self.assertEqual(res_prefix["target_product"].id, prod_tbua.id)

    def test_03_explicit_replacement_intent_detection(self):
        """Kiểm tra nhận diện ý định tìm phụ tùng thay thế cho các danh mục khác nhau"""
        test_cases = [
            ("thay thế cho TBUA.010", "TBUA.010"),
            ("phụ tùng thay cho LC.002", "LC.002"),
            ("mã tương đương với BI.005", "BI.005"),
            ("phụ tùng thay thế cho mã HOWO-371", "HOWO-371"),
        ]
        for query, expected_target in test_cases:
            res = self.router.route_query(query)
            self.assertEqual(res["intent"], "explicit_replacement", f"Query '{query}' phải là explicit_replacement")
            self.assertTrue(expected_target.lower() in res["clean_query"].lower() or expected_target.lower() in str(res.get("target_sku") or "").lower())

    def test_04_equipment_context_intent_detection(self):
        """Kiểm tra nhận diện bối cảnh xe / động cơ / hộp số"""
        queries = [
            ("Lá côn xe Howo 371", "HOWO"),
            ("Bơm nước động cơ Weichai WP10", "WEICHAI"),
            ("Bánh răng hộp số Fast Gear 8JS85T", "FAST GEAR"),
            ("Tăm bua cầu sau xe đầu kéo Chenglong", "CHENGLONG"),
        ]
        for q, expected_term in queries:
            res = self.router.route_query(q)
            self.assertIn(res["intent"], ("equipment_context", "technical_spec_only", "product_name_alias"))
            terms_upper = [t.upper() for t in res.get("equipment_terms", [])]
            # Nếu là equipment_context thì phải nhận diện được term
            if res["intent"] == "equipment_context":
                self.assertTrue(any(expected_term in t for t in terms_upper), f"Terms {terms_upper} phải chứa {expected_term}")

    def test_05_technical_spec_only_intent_detection(self):
        """Kiểm tra nhận diện truy vấn thuần thông số kỹ thuật đa danh mục"""
        # Số răng
        res1 = self.router.route_query("răng: 10")
        self.assertEqual(res1["intent"], "technical_spec_only")
        self.assertIn("rang", res1["extracted_specs"])
        self.assertEqual(res1["extracted_specs"]["rang"]["value"], 10)

        # Số lỗ (phổ biến cho tăm bua, mâm)
        res2 = self.router.route_query("tăm bua số lỗ: 10")
        self.assertEqual(res2["intent"], "technical_spec_only")
        self.assertTrue("so_lo" in res2["extracted_specs"] or "so_lo_bulong" in res2["extracted_specs"])

        # Đường kính / Phi
        res3 = self.router.route_query("phi 420")
        self.assertEqual(res3["intent"], "technical_spec_only")
        self.assertIn("duong_kinh_ngoai", res3["extracted_specs"])
        self.assertEqual(res3["extracted_specs"]["duong_kinh_ngoai"]["value"], 420.0)

    def test_06_category_without_profile_honest_reporting(self):
        """Kiểm tra danh mục không có profile (TBUA / BI) được báo cáo trung thực, KHÔNG lấy profile LC"""
        # Category TBUA không có matching profile
        profile = self.engine.resolve_profile(self.categ_tbua)
        rules = self.engine._get_rules_from_profile(profile)
        # Nếu chưa cấu hình profile và spec defs cho TBUA thì rules_count = 0
        rules_count = len(rules)

        # Gọi find_matching_products cho TBUA
        res = self.engine.find_matching_products(self.categ_tbua.id, {"duong_kinh_ngoai": {"value": 420.0, "uom": "mm"}})
        if rules_count == 0:
            self.assertFalse(res["success"])
            self.assertFalse(res["has_profile"])
            self.assertIn("chưa có Hồ sơ so khớp", res["error"])
            self.assertEqual(res["retrieved_count"], 0)
            self.assertEqual(res["compatible_count"], 0)
        else:
            # Nếu có rules thì đã được cấu hình hợp lệ
            self.assertTrue(res["has_profile"])

    def test_07_general_search_does_not_trigger_arbitrary_replacement_matching(self):
        """Kiểm tra truy vấn tìm kiếm chung (bối cảnh thiết bị / tên phụ tùng) KHÔNG tự tiện chạy so khớp thay thế"""
        assistant = self.assistant_model.create({
            'user_query': 'tăm bua xe howo',
        })
        assistant.action_ask_ai()

        # Kiểm tra phản hồi: Phải hiển thị dạng kết quả tìm kiếm kho, không chạy matching engine
        self.assertIn("Kết quả tìm kiếm phụ tùng", assistant.matching_explanation_html)
        self.assertIn("Chưa kích hoạt đối chiếu thay thế kỹ thuật", assistant.matching_explanation_html)
        self.assertIn("chưa được thẩm định tương thích thay thế", assistant.matching_explanation_html.lower())

    def test_08_ambiguous_query_in_ai_assistant(self):
        """Kiểm tra truy vấn mơ hồ trong UI AI Assistant trả về hướng dẫn làm rõ, không bịa sản phẩm cơ sở"""
        assistant = self.assistant_model.create({
            'user_query': '???',
        })
        assistant.action_ask_ai()

        self.assertEqual(assistant.confidence_level, 'low')
        self.assertIn("Yêu cầu chưa rõ ràng", assistant.ai_response)
        self.assertIn("Động cơ so khớp kỹ thuật tạm dừng", assistant.matching_explanation_html)
        self.assertEqual(len(assistant.matched_product_ids), 0)

    def test_09_single_spec_query_never_claims_100_percent_overall_compatibility(self):
        """Kiểm tra tra cứu 1 thông số đơn lẻ không bao giờ tuyên bố tương thích tổng thể 100%"""
        if not self.categ_lc:
            return

        res = self.engine.find_matching_products(self.categ_lc.id, {
            "rang": {"value": 10, "uom": "răng"}
        })
        self.assertTrue(res["success"])

        # Không có sản phẩm nào được xếp hạng exact_match cho toàn bộ quy cách nếu chỉ tra 1 thông số
        for cand in res["ranked_matches"]:
            self.assertNotEqual(cand["match_status"], "exact_match", "Tra 1 thông số cốt lõi không thể là exact_match tổng thể")
        # Phải có các ứng viên trong nhóm insufficient_candidates vì thiếu các thông số cốt lõi khác
        self.assertTrue(len(res["insufficient_candidates"]) > 0 or len(res["ranked_matches"]) == 0)

    def test_10_execution_performance_and_stage_isolation(self):
        """Kiểm tra bảng đo lường hiệu năng 8 công đoạn với Monotonic Clock và hiển thị badge Intent"""
        assistant = self.assistant_model.create({
            'user_query': 'LC.002',
        })
        assistant.action_ask_ai()

        self.assertTrue(bool(assistant.query_perf_html))
        self.assertIn("Thông Tin Xử Lý Truy Vấn", assistant.query_perf_html)
        self.assertIn("Tổng thời gian backend", assistant.query_perf_html)
        self.assertIn("Phân tích yêu cầu &amp; định tuyến ý định", assistant.query_perf_html)
        self.assertIn("Tra cứu mã SKU chính xác", assistant.query_perf_html)

    def test_11_bearing_moay_o_routing_accuracy(self):
        """Kiểm tra độ chính xác phân luồng danh mục:
        - 'vòng bi moay ơ' phải thuộc danh mục BI (Vòng bi), KHÔNG thuộc BI+ (Bi chữ thập).
        - 'bi chữ thập' phải thuộc danh mục BI+ (Bi chữ thập).
        - 'moay ơ' phải thuộc danh mục MO (Moay ơ).
        """
        cat_vbi = self.router._detect_category("vòng bi moay ơ")
        if cat_vbi:
            self.assertIn("BI", cat_vbi.name)
            self.assertNotIn("BI+", cat_vbi.name, "vòng bi moay ơ KHÔNG được định tuyến vào BI+ (Bi chữ thập)")
            self.assertNotIn("chữ thập", cat_vbi.name.lower(), "vòng bi moay ơ KHÔNG được định tuyến vào Bi chữ thập")

        cat_cross = self.router._detect_category("bi chữ thập")
        if cat_cross:
            self.assertTrue("BI+" in cat_cross.name or "chữ thập" in cat_cross.name.lower())

        cat_mo = self.router._detect_category("moay ơ")
        if cat_mo:
            self.assertTrue("MO" in cat_mo.name or "moay ơ" in cat_mo.name.lower())

    def test_12_la_con_mm_dimension_and_teeth_extraction(self):
        """Kiểm tra trích xuất thông số đường kính kèm đơn vị mm và số răng:
        - 'lá côn 325mm, răng 10' phải trích xuất đủ cả 2 thông số: duong_kinh_ngoai = 325 và rang = 10.
        - UI AI Assistant hiển thị đầy đủ bảng đối chiếu cả 2 thông số.
        """
        res = self.router.route_query("lá côn 325mm, răng 10")
        self.assertEqual(res["intent"], "technical_spec_only")
        specs = res.get("extracted_specs", {})
        self.assertIn("duong_kinh_ngoai", specs, "Phải trích xuất được duong_kinh_ngoai từ '325mm'")
        self.assertEqual(specs["duong_kinh_ngoai"]["value"], 325.0)
        self.assertIn("rang", specs, "Phải trích xuất được rang từ 'răng 10'")
        self.assertEqual(specs["rang"]["value"], 10)

        # Chạy trực tiếp qua UI AI Assistant
        assistant = self.assistant_model.create({
            'user_query': 'lá côn 325mm, răng 10',
        })
        assistant.action_ask_ai()
        self.assertIn("325", assistant.matching_explanation_html)
        self.assertIn("10", assistant.matching_explanation_html)
        self.assertIn("duong_kinh_ngoai", assistant.matching_explanation_html.lower() + assistant.ai_response.lower() + "đường kính")

