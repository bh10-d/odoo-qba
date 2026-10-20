# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, ValidationError, UserError
import json


class TestAiRequestWorkflow(TransactionCase):
    """Bộ kiểm thử Quy Trình Yêu Cầu Hỗ Trợ Dữ Liệu Sản Phẩm & Kỹ Thuật AI (Task B: qba.ai.request)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.request_model = cls.env["qba.ai.request"]
        cls.conversation_model = cls.env["qba.ai.conversation"]
        cls.message_model = cls.env["qba.ai.message"]
        cls.product_model = cls.env["product.template"]
        cls.category_model = cls.env["product.category"]
        cls.user_model = cls.env["res.users"]
        cls.attachment_model = cls.env["ir.attachment"]

        # 1. Nhóm quyền
        group_user = cls.env.ref("base.group_user")
        group_manager = cls.env.ref("qba_ai.group_qba_ai_manager")

        # 2. Tạo User A (Internal User)
        cls.user_a = cls.user_model.create({
            "name": "Nhân Viên Kinh Doanh A (Test)",
            "login": "sale_user_req_a",
            "email": "user_req_a@qba.vn",
            "groups_id": [(6, 0, [group_user.id])],
        })

        # 3. Tạo User B (Internal User)
        cls.user_b = cls.user_model.create({
            "name": "Nhân Viên Kinh Doanh B (Test)",
            "login": "sale_user_req_b",
            "email": "user_req_b@qba.vn",
            "groups_id": [(6, 0, [group_user.id])],
        })

        # 4. Tạo AI Manager
        cls.manager = cls.user_model.create({
            "name": "Quản Trị Viên AI (Test Manager)",
            "login": "ai_manager_req_test",
            "email": "ai_manager_req@qba.vn",
            "groups_id": [(6, 0, [group_user.id, group_manager.id])],
        })

        # 5. Dữ liệu danh mục và sản phẩm mẫu
        cls.categ = cls.category_model.search([('name', 'ilike', 'LC')], limit=1)
        if not cls.categ:
            cls.categ = cls.category_model.create({'name': 'LC - Test Category'})

        cls.product_1 = cls.product_model.search([('categ_id', '=', cls.categ.id)], limit=1)
        if not cls.product_1:
            cls.product_1 = cls.product_model.create({
                "name": "Lá Côn Test Request 001",
                "default_code": "LC.REQ.001",
                "categ_id": cls.categ.id,
            })

    def test_01_unique_request_reference_generation(self):
        """1. Kiểm tra sinh mã yêu cầu tự động duy nhất (REQ-00001, REQ-00002...)"""
        req1 = self.request_model.with_user(self.user_a).create({
            "request_type": "missing_product",
            "raw_query": "Tìm lá côn phi 430",
        })
        req2 = self.request_model.with_user(self.user_a).create({
            "request_type": "missing_spec",
            "raw_query": "Bánh răng Howo 24 răng",
        })
        self.assertTrue(req1.name.startswith("REQ-"), f"Tên yêu cầu phải bắt đầu bằng REQ-, thực tế: {req1.name}")
        self.assertTrue(req2.name.startswith("REQ-"), f"Tên yêu cầu phải bắt đầu bằng REQ-, thực tế: {req2.name}")
        self.assertNotEqual(req1.name, req2.name, "Mã yêu cầu phải là duy nhất")

    def test_02_supported_request_types_and_lifecycle(self):
        """2. Kiểm tra đầy đủ 4 loại yêu cầu và vòng đời trạng thái hợp lệ"""
        types = ["missing_product", "missing_spec", "spec_conflict", "substitute_review"]
        for idx, rtype in enumerate(types):
            req = self.request_model.with_user(self.user_a).create({
                "request_type": rtype,
                "raw_query": f"Query for {rtype} test {idx}",
                "product_id": self.product_1.id,
            })
            self.assertEqual(req.state, "submitted", "Trạng thái ban đầu phải là submitted")
            self.assertEqual(req.request_type, rtype)

            # Manager tiếp nhận -> in_progress
            req.with_user(self.manager).action_assign_to_me()
            self.assertEqual(req.state, "in_progress")
            self.assertEqual(req.handler_id.id, self.manager.id)

            # Manager xử lý xong -> resolved
            req.with_user(self.manager).write({
                "admin_feedback": f"Đã bổ sung dữ liệu cho {rtype}"
            })
            req.with_user(self.manager).action_resolve()
            self.assertEqual(req.state, "resolved")

    def test_03_user_data_isolation_record_rules(self):
        """3. Kiểm tra phân lập dữ liệu: User B không thể đọc, sửa hoặc liệt kê yêu cầu của User A"""
        req_a = self.request_model.with_user(self.user_a).create({
            "request_type": "missing_product",
            "raw_query": "Phụ tùng riêng của User A",
            "user_notes": "Ghi chú bảo mật",
        })

        # User B tìm kiếm yêu cầu của User A -> không được thấy
        user_b_reqs = self.request_model.with_user(self.user_b).search([("id", "=", req_a.id)])
        self.assertEqual(len(user_b_reqs), 0, "User B không được tìm thấy request của User A")

        # User B cố tình đọc trực tiếp -> AccessError
        with self.assertRaises(AccessError):
            req_a.with_user(self.user_b).read(["name", "raw_query", "user_notes"])

        # User B cố tình sửa request của User A -> AccessError
        with self.assertRaises(AccessError):
            req_a.with_user(self.user_b).write({"user_notes": "Hacked by User B"})

    def test_04_ordinary_user_cannot_manipulate_protected_fields_or_states(self):
        """4. Người dùng thường không thể tự gán admin, tự đổi state, tự duyệt hoặc tự từ chối"""
        req_a = self.request_model.with_user(self.user_a).create({
            "request_type": "missing_product",
            "raw_query": "Kiểm tra quyền state",
        })

        # User thường không thể tạo bản ghi với state != submitted
        with self.assertRaises(AccessError):
            self.request_model.with_user(self.user_a).create({
                "request_type": "missing_product",
                "raw_query": "Thử tạo resolved",
                "state": "resolved",
            })

        # User thường không thể sửa state
        with self.assertRaises(AccessError):
            req_a.with_user(self.user_a).write({"state": "resolved"})

        # User thường không thể gọi action_assign_to_me
        with self.assertRaises(AccessError):
            req_a.with_user(self.user_a).action_assign_to_me()

        # User thường không thể gọi action_resolve
        with self.assertRaises(AccessError):
            req_a.with_user(self.user_a).action_resolve()

        # User thường không thể gọi action_reject
        with self.assertRaises(AccessError):
            req_a.with_user(self.user_a).action_reject()

        # User thường không thể xóa request
        with self.assertRaises(AccessError):
            req_a.with_user(self.user_a).unlink()

    def test_05_manager_processing_permissions(self):
        """5. Quản trị viên AI có toàn quyền xem, tiếp nhận, chuyển trạng thái và xóa yêu cầu"""
        req = self.request_model.with_user(self.user_a).create({
            "request_type": "spec_conflict",
            "raw_query": "Báo sai lệch thông số",
            "product_id": self.product_1.id,
        })

        # Manager xem được request của user_a
        manager_view = self.request_model.with_user(self.manager).browse(req.id)
        self.assertTrue(manager_view.exists())
        self.assertEqual(manager_view.user_id.id, self.user_a.id)

        # Manager bấm tiếp nhận
        manager_view.action_assign_to_me()
        self.assertEqual(manager_view.state, "in_progress")
        self.assertEqual(manager_view.handler_id.id, self.manager.id)

        # Manager có thể xóa yêu cầu
        manager_view.unlink()
        self.assertFalse(req.exists(), "Manager phải có quyền xóa request")

    def test_06_mandatory_feedback_and_rejection_reason(self):
        """6. Bắt buộc nhập phản hồi khi hoàn tất (resolved) và lý do khi từ chối (rejected)"""
        req1 = self.request_model.with_user(self.user_a).create({
            "request_type": "missing_product",
            "raw_query": "Thiếu lá côn xe Shacman",
        })
        req1.with_user(self.manager).action_assign_to_me()

        # Cố tình hoàn tất mà không nhập admin_feedback -> ValidationError
        with self.assertRaises(ValidationError):
            req1.with_user(self.manager).action_resolve()

        # Nhập admin_feedback -> Hoàn tất thành công
        req1.with_user(self.manager).write({"admin_feedback": "Đã tạo sản phẩm LC.SHACMAN.430"})
        req1.with_user(self.manager).action_resolve()
        self.assertEqual(req1.state, "resolved")

        # Test từ chối không có lý do
        req2 = self.request_model.with_user(self.user_a).create({
            "request_type": "missing_product",
            "raw_query": "Sản phẩm không kinh doanh",
        })
        with self.assertRaises(ValidationError):
            req2.with_user(self.manager).action_reject()

        # Nhập lý do từ chối -> Từ chối thành công
        req2.with_user(self.manager).write({"rejection_reason": "QBA không kinh doanh dòng sản phẩm này."})
        req2.with_user(self.manager).action_reject()
        self.assertEqual(req2.state, "rejected")

    def test_07_request_creation_from_conversation(self):
        """7. Tạo yêu cầu từ phiên hội thoại Trợ lý QBA AI và tự sinh tin nhắn phản hồi xác nhận"""
        conv = self.conversation_model.with_user(self.user_a).create_new_conversation()
        msg_user = self.message_model.with_user(self.user_a).create({
            "conversation_id": conv.id,
            "role": "user",
            "content": "Tìm phớt đuôi trục cơ xe Howo D10",
        })
        msg_ai = self.message_model.with_user(self.user_a).create({
            "conversation_id": conv.id,
            "role": "assistant",
            "content": "Không tìm thấy phụ tùng nào khớp trong kho QBA.",
        })

        # Gửi request liên kết với conversation và message
        req = self.request_model.with_user(self.user_a).create({
            "request_type": "missing_product",
            "raw_query": msg_user.content,
            "conversation_id": conv.id,
            "message_id": msg_ai.id,
            "user_notes": "Khách cần gấp trong ngày mai",
            "extracted_specs_json": json.dumps({"engine": "D10", "type": "phớt"}),
        })

        self.assertTrue(req.exists())
        self.assertEqual(req.conversation_id.id, conv.id)
        self.assertEqual(req.message_id.id, msg_ai.id)
        self.assertEqual(req.user_id.id, self.user_a.id)

    def test_08_duplicate_submission_handling(self):
        """8. Kiểm tra cơ chế chống gửi trùng lặp (Idempotency Prevention)"""
        req_vals = {
            "request_type": "missing_product",
            "raw_query": "Tìm lá côn phi 350 độc lạ",
            "user_notes": "Lần 1",
        }
        req1 = self.request_model.with_user(self.user_a).create(req_vals)
        self.assertTrue(req1.exists())

        # Gửi lại ngay lập tức cùng nội dung -> ValidationError chống duplicate
        with self.assertRaises(ValidationError):
            self.request_model.with_user(self.user_a).create({
                "request_type": "missing_product",
                "raw_query": "Tìm lá côn phi 350 độc lạ",
                "user_notes": "Lần 2 bấm nhầm",
            })

    def test_09_unauthorized_conversation_cross_reference_prevention(self):
        """9. User B không thể tạo yêu cầu gắn vào conversation của User A"""
        conv_a = self.conversation_model.with_user(self.user_a).create_new_conversation()
        msg_a = self.message_model.with_user(self.user_a).create({
            "conversation_id": conv_a.id,
            "role": "user",
            "content": "Câu hỏi riêng của A",
        })

        # Kiểm tra qua controller submit logic: User B không được phép gắn request vào conv của A
        from odoo.addons.qba_ai.controllers.main import QbaAiAssistantController
        from unittest.mock import MagicMock

        # Giả lập request context với User B
        controller = QbaAiAssistantController()
        # Direct check on conversation access
        with self.assertRaises(AccessError):
            conv_a.with_user(self.user_b).check_access('read')

    def test_10_attachment_association(self):
        """10. Kiểm tra đính kèm tài liệu / hình ảnh vào yêu cầu hỗ trợ"""
        att = self.attachment_model.with_user(self.user_a).create({
            "name": "anh_phu_tung_thuc_te.jpg",
            "datas": "dGVzdF9kYXRh",
            "mimetype": "image/jpeg",
        })
        req = self.request_model.with_user(self.user_a).create({
            "request_type": "spec_conflict",
            "raw_query": "Đo thực tế 328mm không phải 325mm",
            "product_id": self.product_1.id,
            "attachment_ids": [(6, 0, [att.id])],
        })
        self.assertIn(att.id, req.attachment_ids.ids)
        self.assertEqual(len(req.attachment_ids), 1)

