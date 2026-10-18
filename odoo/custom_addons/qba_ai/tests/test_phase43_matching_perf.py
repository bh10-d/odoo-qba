# -*- coding: utf-8 -*-
import time
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError


class TestPhase43MatchingPerf(TransactionCase):
    """PHASE 4.3 — Bộ test tự động kiểm thử độ chính xác matching,
    tính đầy đủ của bảng đối chiếu và hệ thống đo lường hiệu năng.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env["qba.spec.matching.engine"]

        # Nhóm quyền
        cls.group_ai_user = cls.env.ref("qba_ai.group_qba_ai_user")
        cls.group_ai_manager = cls.env.ref("qba_ai.group_qba_ai_manager")

        # 1. Danh mục thử nghiệm riêng biệt cho P43
        cls.categ_lc = cls.env["product.category"].create({"name": "P43_LC_CATEGORY"})

        # 2. Khởi tạo 5 thông số cốt lõi cho LC
        cls.spec_teeth = cls._get_or_create_spec("p43_lc_teeth", "Số răng moay ơ LC", "integer", "răng", [cls.categ_lc.id], True)
        cls.spec_diam = cls._get_or_create_spec("p43_lc_diam", "Đường kính ngoài LC", "float", "mm", [cls.categ_lc.id], True)
        cls.spec_springs = cls._get_or_create_spec("p43_lc_springs", "Số lò xo LC", "integer", "lò xo", [cls.categ_lc.id], True)
        cls.spec_hub_c = cls._get_or_create_spec("p43_lc_hub_c", "Đường kính moay ơ C", "float", "mm", [cls.categ_lc.id], True)
        cls.spec_hub_d = cls._get_or_create_spec("p43_lc_hub_d", "Đường kính moay ơ D", "float", "mm", [cls.categ_lc.id], True)

        # 3. Tạo Profile so khớp với đầy đủ 5 rules cốt lõi
        cls.profile = cls.env["qba.category.matching.profile"].create({
            "name": "P43 Test Profile LC",
            "category_id": cls.categ_lc.id,
            "min_score_threshold": 80.0,
            "allow_partial_match": True,
        })
        cls.rule_teeth = cls.env["qba.category.matching.rule"].create({
            "profile_id": cls.profile.id,
            "spec_definition_id": cls.spec_teeth.id,
            "match_type": "exact",
            "weight": 20.0,
            "is_hard_constraint": True,
        })
        cls.rule_diam = cls.env["qba.category.matching.rule"].create({
            "profile_id": cls.profile.id,
            "spec_definition_id": cls.spec_diam.id,
            "match_type": "tolerance",
            "tolerance_type": "absolute",
            "tolerance_plus": 1.0,
            "tolerance_minus": 1.0,
            "weight": 20.0,
            "is_hard_constraint": True,
        })
        cls.rule_springs = cls.env["qba.category.matching.rule"].create({
            "profile_id": cls.profile.id,
            "spec_definition_id": cls.spec_springs.id,
            "match_type": "exact",
            "weight": 20.0,
            "is_hard_constraint": True,
        })
        cls.rule_hub_c = cls.env["qba.category.matching.rule"].create({
            "profile_id": cls.profile.id,
            "spec_definition_id": cls.spec_hub_c.id,
            "match_type": "exact",
            "weight": 20.0,
            "is_hard_constraint": True,
        })
        cls.rule_hub_d = cls.env["qba.category.matching.rule"].create({
            "profile_id": cls.profile.id,
            "spec_definition_id": cls.spec_hub_d.id,
            "match_type": "exact",
            "weight": 20.0,
            "is_hard_constraint": True,
        })

        # 4. Sản phẩm cơ sở LC.002 (Đầy đủ 5 thông số verified)
        cls.prod_base_lc002 = cls._create_product("Lá Côn Howo LC.002", "LC.002.P43", cls.categ_lc.id, 1500000.0)
        cls._set_spec(cls.prod_base_lc002, cls.spec_teeth, "10", 10, "verified")
        cls._set_spec(cls.prod_base_lc002, cls.spec_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_base_lc002, cls.spec_springs, "8", 8, "verified")
        cls._set_spec(cls.prod_base_lc002, cls.spec_hub_c, "31.0", 31.0, "verified")
        cls._set_spec(cls.prod_base_lc002, cls.spec_hub_d, "38.5", 38.5, "verified")

        # 5. Sản phẩm ứng viên LC.007 (Chỉ có răng, đường kính, lò xo; THIẾU moay-ơ C và D)
        cls.prod_cand_lc007 = cls._create_product("Lá Côn Dongfeng LC.007", "LC.007.P43", cls.categ_lc.id, 1450000.0)
        cls._set_spec(cls.prod_cand_lc007, cls.spec_teeth, "10", 10, "verified")
        cls._set_spec(cls.prod_cand_lc007, cls.spec_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_cand_lc007, cls.spec_springs, "8", 8, "verified")

        # 6. Sản phẩm ứng viên hoàn hảo LC.999 (Khớp đủ cả 5 thông số)
        cls.prod_cand_perfect = cls._create_product("Lá Côn Hoàn Hảo LC.999", "LC.999.P43", cls.categ_lc.id, 1600000.0)
        cls._set_spec(cls.prod_cand_perfect, cls.spec_teeth, "10", 10, "verified")
        cls._set_spec(cls.prod_cand_perfect, cls.spec_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_cand_perfect, cls.spec_springs, "8", 8, "verified")
        cls._set_spec(cls.prod_cand_perfect, cls.spec_hub_c, "31.0", 31.0, "verified")
        cls._set_spec(cls.prod_cand_perfect, cls.spec_hub_d, "38.5", 38.5, "verified")

        # 7. Sản phẩm ứng viên sai răng (Vi phạm hard constraint)
        cls.prod_cand_bad_teeth = cls._create_product("Lá Côn 14 Răng", "LC.BAD.TEETH", cls.categ_lc.id, 1300000.0)
        cls._set_spec(cls.prod_cand_bad_teeth, cls.spec_teeth, "14", 14, "verified")
        cls._set_spec(cls.prod_cand_bad_teeth, cls.spec_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_cand_bad_teeth, cls.spec_springs, "8", 8, "verified")
        cls._set_spec(cls.prod_cand_bad_teeth, cls.spec_hub_c, "31.0", 31.0, "verified")
        cls._set_spec(cls.prod_cand_bad_teeth, cls.spec_hub_d, "38.5", 38.5, "verified")

        # 8. Sản phẩm ứng viên có thông số UNVERIFIED
        cls.prod_cand_unverified = cls._create_product("Lá Côn Chưa Duyệt", "LC.UNVERIFIED", cls.categ_lc.id, 1350000.0)
        cls._set_spec(cls.prod_cand_unverified, cls.spec_teeth, "10", 10, "unverified")
        cls._set_spec(cls.prod_cand_unverified, cls.spec_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_cand_unverified, cls.spec_springs, "8", 8, "verified")
        cls._set_spec(cls.prod_cand_unverified, cls.spec_hub_c, "31.0", 31.0, "verified")
        cls._set_spec(cls.prod_cand_unverified, cls.spec_hub_d, "38.5", 38.5, "verified")

        # 9. Sản phẩm ứng viên VỪA vi phạm hard constraint VỪA thiếu thông số verified
        cls.prod_cand_viol_and_missing = cls._create_product("Lá Côn Sai Răng Thiếu Hub", "LC.VIOL.MISSING", cls.categ_lc.id, 1200000.0)
        cls._set_spec(cls.prod_cand_viol_and_missing, cls.spec_teeth, "14", 14, "verified")
        cls._set_spec(cls.prod_cand_viol_and_missing, cls.spec_diam, "325.0", 325.0, "verified")
        cls._set_spec(cls.prod_cand_viol_and_missing, cls.spec_springs, "8", 8, "verified")
        # Cố ý không gán hub_c và hub_d

    @classmethod
    def _get_or_create_spec(cls, code, name, data_type, uom, category_ids, is_critical):
        spec = cls.env["qba.product.spec.definition"].with_context(active_test=False).search([("code", "=", code)], limit=1)
        if not spec:
            spec = cls.env["qba.product.spec.definition"].create({
                "name": name,
                "code": code,
                "data_type": data_type,
                "uom": uom,
                "category_ids": [(6, 0, category_ids)],
                "is_critical": is_critical,
                "active": True,
            })
        else:
            spec.write({
                "name": name,
                "data_type": data_type,
                "uom": uom,
                "category_ids": [(6, 0, category_ids)],
                "is_critical": is_critical,
                "active": True,
            })
        return spec

    @classmethod
    def _create_product(cls, name, code, categ_id, price):
        return cls.env["product.template"].create({
            "name": name,
            "default_code": code,
            "categ_id": categ_id,
            "list_price": price,
            "standard_price": price * 0.8,
        })

    @classmethod
    def _set_spec(cls, prod, spec_def, val_display, typed_val, status):
        vals = {
            "product_tmpl_id": prod.id,
            "spec_definition_id": spec_def.id,
            "value_display": val_display,
            "validation_status": status,
        }
        if spec_def.data_type == "float":
            vals["value_float"] = float(typed_val)
        elif spec_def.data_type == "integer":
            vals["value_integer"] = int(typed_val)
        elif spec_def.data_type == "boolean":
            vals["value_boolean"] = bool(typed_val)
        else:
            vals["value_char"] = str(typed_val)
        return cls.env["qba.product.spec.value"].create(vals)

    # =========================================================================
    # 14 TEST CASES SECTION 8 THEO YÊU CẦU PHASE 4.3
    # =========================================================================

    def test_01_lc002_retrieves_all_verified_specs(self):
        """1. Input 'LC.002' thu thập đủ tất cả thông số verified, bao gồm cả moay-ơ C và D."""
        res = self.engine.match_product_to_candidates(self.prod_base_lc002.id)
        self.assertTrue(res["success"])

        # Xác minh sản phẩm nguồn có đủ 5 thông số
        base_vals = self.prod_base_lc002.spec_value_ids.filtered(lambda v: v.validation_status == "verified")
        codes = {v.spec_code for v in base_vals}
        self.assertIn("p43_lc_teeth", codes)
        self.assertIn("p43_lc_diam", codes)
        self.assertIn("p43_lc_springs", codes)
        self.assertIn("p43_lc_hub_c", codes)
        self.assertIn("p43_lc_hub_d", codes)

        # Ứng viên hoàn hảo phải khớp 100%
        cand_perfect = next((m for m in res["ranked_matches"] if m["candidate_id"] == self.prod_cand_perfect.id), None)
        self.assertIsNotNone(cand_perfect)
        self.assertEqual(cand_perfect["match_status"], "exact_match")
        self.assertEqual(cand_perfect["match_score"], 100.0)

    def test_02_explanation_table_completeness(self):
        """2. Bảng giải thích kỹ thuật chứa đầy đủ các rule đã đánh giá và thông số còn thiếu.
        Ứng viên LC.007 (thiếu moay-ơ C và D) KHÔNG được 100% và bị từ chối với lý do thiếu thông số.
        """
        res = self.engine.match_product_to_candidates(self.prod_base_lc002.id)
        self.assertTrue(res["success"])

        # LC.007 phải nằm trong danh sách rejected_candidates hoặc có status là insufficient_data
        rejected_ids = [c["candidate_id"] for c in res["rejected_candidates"]]
        self.assertIn(self.prod_cand_lc007.id, rejected_ids)

        cand_lc007 = next(c for c in res["rejected_candidates"] if c["candidate_id"] == self.prod_cand_lc007.id)
        self.assertEqual(cand_lc007["match_status"], "insufficient_data")
        self.assertEqual(cand_lc007["match_score"], 0.0)
        self.assertTrue(any("Đường kính moay ơ C" in m["spec_name"] or "Đường kính moay ơ D" in m["spec_name"]
                            for m in cand_lc007["missing_critical_specs"]))

        # Kiểm tra lý do từ chối và thông số thiếu của LC.007
        self.assertIn("Thiếu", cand_lc007["status_reason"])
        missing_codes = {m["spec_code"] for m in cand_lc007["missing_critical_specs"]}
        self.assertIn("p43_lc_hub_c", missing_codes)
        self.assertIn("p43_lc_hub_d", missing_codes)

        # Kiểm tra bảng HTML sinh ra cho candidate bị thiếu thông số
        cand_html = self.engine.format_explanation(cand_lc007)
        self.assertIn("Thiếu", cand_html)
        self.assertIn("Đường kính moay ơ C", cand_html)

        # Kiểm tra bảng HTML của kết quả matching tổng thể chứa đủ 5 thông số đối chiếu của ứng viên đạt chuẩn
        html = res["explanation_html"]
        self.assertIn("Đường kính moay ơ C", html)
        self.assertIn("Đường kính moay ơ D", html)

    def test_03_single_spec_not_100_overall(self):
        """3. Input 'răng: 10' không được phong lên 100% tương thích tổng thể.
        spec_match_score = 100%, nhưng status = insufficient_data, KHÔNG tự động coi là tương thích thay thế được.
        """
        res = self.engine.find_matching_products(self.categ_lc.id, {"p43_lc_teeth": 10})
        self.assertTrue(res["success"])
        # Không có ranked_matches nào được đề xuất thay thế toàn diện khi chỉ có 1 thông số
        self.assertEqual(len(res["ranked_matches"]), 0)
        self.assertTrue(len(res["insufficient_candidates"]) >= 1)

        # Tìm ứng viên có 10 răng đã duyệt (ví dụ prod_cand_perfect)
        cand_perfect = next(c for c in res["insufficient_candidates"] if c["candidate_id"] == self.prod_cand_perfect.id)
        # Status phải là insufficient_data, KHÔNG ĐƯỢC là exact_match hay partial_match
        self.assertEqual(cand_perfect["match_status"], "insufficient_data")
        self.assertEqual(cand_perfect["compatibility_status"], "insufficient_data")
        self.assertEqual(cand_perfect["spec_match_score"], 100.0)
        self.assertEqual(cand_perfect["match_score"], 0.0)
        # Lý do phải nêu rõ chưa đủ dữ liệu xác nhận tương thích tổng thể
        self.assertIn("Chưa đủ dữ liệu", cand_perfect["status_reason"])

        # Toàn bộ insufficient_candidates đều phải có status là insufficient_data (không ai được xếp vào exact_match hay partial_match)
        for match in res["insufficient_candidates"]:
            self.assertEqual(match["match_status"], "insufficient_data")
            self.assertEqual(match["compatibility_status"], "insufficient_data")

        # Kiểm tra nhãn HTML không hiển thị 'Khớp chính xác 100%' mà hiển thị Chưa đủ dữ liệu xác thực
        html = res["explanation_html"]
        self.assertIn("Chưa đủ dữ liệu xác thực (Insufficient Data)", html)
        self.assertNotIn("Khớp chính xác 100% tất cả thông số", html)

    def test_04_hard_constraint_elimination(self):
        """4. Hard constraint vi phạm lập tức loại candidate dù các thông số khác đạt 100%."""
        eval_bad = self.engine.evaluate_candidate(
            self.prod_cand_bad_teeth,
            {"p43_lc_teeth": 10, "p43_lc_diam": 325.0, "p43_lc_springs": 8, "p43_lc_hub_c": 31.0, "p43_lc_hub_d": 38.5},
            self.profile
        )
        self.assertEqual(eval_bad["match_status"], "mismatch")
        self.assertEqual(eval_bad["match_score"], 0.0)
        self.assertTrue(len(eval_bad["violated_hard_constraints"]) >= 1)
        self.assertEqual(eval_bad["violated_hard_constraints"][0]["spec_code"], "p43_lc_teeth")

    def test_05_missing_or_unverified_safe_status(self):
        """5. Dữ liệu thiếu/chưa duyệt trả về trạng thái an toàn (insufficient data / unverified)."""
        eval_unv = self.engine.evaluate_candidate(
            self.prod_cand_unverified,
            {"p43_lc_teeth": 10, "p43_lc_diam": 325.0, "p43_lc_springs": 8, "p43_lc_hub_c": 31.0, "p43_lc_hub_d": 38.5},
            self.profile
        )
        self.assertEqual(eval_unv["match_status"], "insufficient_data")
        self.assertEqual(eval_unv["match_score"], 0.0)
        self.assertTrue(eval_unv["has_unverified_data"])

    def test_06_partial_query_score_contextualized(self):
        """6. 100% score chỉ xuất hiện khi khớp thực sự trên phạm vi đã đối chiếu
        và kèm ghi chú phạm vi nếu là partial query.
        """
        res = self.engine.find_matching_products(self.categ_lc.id, {"p43_lc_teeth": 10})
        self.assertTrue(res["success"])
        cand = res["insufficient_candidates"][0]
        # Điểm thông số đã đối chiếu là 100%, nhưng status là insufficient_data
        self.assertTrue(cand["is_partial_query"])
        self.assertEqual(cand["spec_match_score"], 100.0)
        self.assertEqual(cand["match_status"], "insufficient_data")

    def test_07_stage_timings_monotonic_clock(self):
        """7. Đo thời gian từng chặng và tổng thời gian được ghi nhận bằng time.perf_counter()."""
        assistant = self.env["qba.ai.assistant"].create({
            "user_query": self.prod_base_lc002.default_code,
        })
        assistant.action_ask_ai()
        self.assertTrue(assistant.query_perf_html)
        self.assertIn("Thông Tin Xử Lý Truy Vấn", assistant.query_perf_html)
        self.assertIn("Tổng thời gian backend", assistant.query_perf_html)

    def test_08_unexecuted_stages_display_na(self):
        """8. Các chặng không thực thi hiển thị đúng 'Không thực hiện' / N/A, không sinh số liệu giả."""
        assistant = self.env["qba.ai.assistant"].create({
            "user_query": self.prod_base_lc002.default_code,
        })
        assistant.action_ask_ai()
        # Đối với tra cứu sản phẩm kỹ thuật xác định, AI call được bỏ qua (skipped)
        self.assertIn("Không thực hiện", assistant.query_perf_html)

    def test_09_ai_fallback_status_recorded(self):
        """9. Timeout hoặc fallback AI được ghi nhận đúng trạng thái trong metrics."""
        assistant = self.env["qba.ai.assistant"].create({
            "user_query": "Một câu hỏi chung chung về phụ tùng không có trong database 123456",
        })
        with patch.object(type(self.env["qba.ai.service"]), "call_gemini_api", side_effect=Exception("API Timeout")):
            assistant.action_ask_ai()
        self.assertTrue(assistant.query_perf_html)
        self.assertTrue("fallback" in assistant.query_perf_html.lower() or "dự phòng" in assistant.query_perf_html.lower())

    def test_10_timing_isolation_between_requests(self):
        """10. Metric giữa 2 request liên tiếp không bị lẫn dữ liệu của nhau."""
        assistant1 = self.env["qba.ai.assistant"].create({"user_query": self.prod_base_lc002.default_code})
        assistant1.action_ask_ai()

        assistant2 = self.env["qba.ai.assistant"].create({"user_query": "Câu hỏi số 2 hoàn toàn khác biệt"})
        assistant2.action_ask_ai()

        # Kiểm tra hai bản ghi có query_perf_html riêng biệt
        self.assertNotEqual(assistant1.query_perf_html, assistant2.query_perf_html)

    def test_11_perf_error_resilience(self):
        """11. Lỗi đo lường hiệu năng không làm hỏng kết quả matching kỹ thuật."""
        assistant = self.env["qba.ai.assistant"].create({"user_query": self.prod_base_lc002.default_code})
        with patch.object(type(assistant), "_format_performance_metrics_html", side_effect=Exception("Render error")):
            assistant.action_ask_ai()
        # Kết quả matching vẫn phải được lưu trữ và hiển thị đầy đủ
        self.assertTrue(assistant.matched_product_ids)
        self.assertIn("Không thể hiển thị thông tin đo lường hiệu năng", assistant.query_perf_html)

    def test_12_ui_displays_genuine_backend_timing(self):
        """12. UI hiển thị thời gian backend thực tế thay vì loading ước lượng."""
        assistant = self.env["qba.ai.assistant"].create({"user_query": self.prod_base_lc002.default_code})
        assistant.action_ask_ai()
        html = assistant.query_perf_html
        self.assertIn("Thông Tin Xử Lý Truy Vấn", html)
        self.assertIn("Tổng thời gian backend", html)
        self.assertIn("Backend Verified", html)
        self.assertIn("table", html)
        self.assertIn("badge", html)

    def test_13_pure_readonly_no_side_effects(self):
        """13. Không sửa giá, tồn kho, SKU của sản phẩm trong toàn bộ luồng matching."""
        price_before = self.prod_base_lc002.list_price
        code_before = self.prod_base_lc002.default_code
        name_before = self.prod_base_lc002.name

        assistant = self.env["qba.ai.assistant"].create({"user_query": self.prod_base_lc002.default_code})
        assistant.action_ask_ai()

        self.assertEqual(self.prod_base_lc002.list_price, price_before)
        self.assertEqual(self.prod_base_lc002.default_code, code_before)
        self.assertEqual(self.prod_base_lc002.name, name_before)

    def test_14_regression_suite_pass(self):
        """14. Regression test: toàn bộ cấu trúc Matching Engine và quyền hạn tiếp tục đảm bảo an toàn."""
        self.assertTrue(hasattr(self.engine, "find_matching_products"))
        self.assertTrue(hasattr(self.engine, "match_product_to_candidates"))
        self.assertTrue(hasattr(self.engine, "evaluate_candidate"))
        self.assertTrue(hasattr(self.engine, "rank_candidates"))

    def test_15_candidate_violation_and_missing_data_both_recorded(self):
        """15. Candidate vừa vi phạm hard constraint vừa thiếu thông số:
        Ghi nhận rõ cả hai yếu tố, phân loại ưu tiên vi phạm bắt buộc (mismatch).
        """
        eval_res = self.engine.evaluate_candidate(
            self.prod_cand_viol_and_missing,
            {"p43_lc_teeth": 10, "p43_lc_diam": 325.0, "p43_lc_springs": 8, "p43_lc_hub_c": 31.0, "p43_lc_hub_d": 38.5},
            self.profile
        )
        self.assertEqual(eval_res["match_status"], "mismatch")
        self.assertTrue(eval_res["has_violation"])
        self.assertTrue(eval_res["has_missing_data"])
        self.assertTrue(len(eval_res["violated_hard_constraints"]) >= 1)
        self.assertTrue(len(eval_res["missing_critical_specs"]) >= 1)
        self.assertIn("Vi phạm", eval_res["status_reason"])
        self.assertIn("thiếu dữ liệu xác thực", eval_res["status_reason"])

    def test_16_timing_sub_millisecond_formatting(self):
        """16. Đo lường timing: các công đoạn < 1 ms không hiển thị 0.000 s mà hiển thị định dạng phù hợp."""
        assistant = self.env["qba.ai.assistant"].create({
            "user_query": self.prod_base_lc002.default_code,
        })
        html = assistant._format_performance_metrics_html(
            req_id="REQ-TEST",
            t_parse=0.00015,
            t_search=0.0005,
            t_retrieval=0.0002,
            t_load_specs=0.0003,
            t_eval=0.0004,
            t_rank_explain=0.0001,
            t_ai=None,
            t_total=0.00165,
            ai_status="skipped",
        )
        self.assertIn("&lt; 0.001</b> s", html)
        self.assertIn("0.15 ms", html)
        self.assertIn("Không thực hiện", html)

    def test_17_rejected_candidates_table_in_assistant(self):
        """17. Bảng giải thích rejected candidates phân loại rõ Insufficient Data và Mismatch."""
        assistant = self.env["qba.ai.assistant"].create({
            "user_query": self.prod_base_lc002.default_code,
        })
        assistant.action_ask_ai()
        html = assistant.matching_explanation_html
        self.assertTrue(html)
        self.assertIn("Nhóm Chưa Đủ Dữ Liệu Xác Thực", html)
        self.assertIn("Đường kính moay ơ C", html)
        self.assertIn("Chưa có dữ liệu verified", html)
        self.assertIn("Hard constraint: Không thể thay thế", html)
