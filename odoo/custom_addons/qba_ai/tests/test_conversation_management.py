# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, ValidationError, UserError


class TestConversationManagement(TransactionCase):
    """Bộ kiểm thử hồi quy toàn diện cho chức năng Quản lý phiên hội thoại & Mở Trợ lý AI (Requirement 8.1 - 8.12)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conv_model = cls.env["qba.ai.conversation"]
        cls.message_model = cls.env["qba.ai.message"]

        # 1. User thông thường (Nhân viên kỹ thuật/kinh doanh)
        cls.user_test = cls.env["res.users"].create({
            "name": "Normal AI User Conv Test",
            "login": "normal_conv_user_test",
            "email": "normal_conv_user@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("qba_ai.group_qba_ai_user").id])],
        })

        # 2. User thứ hai để kiểm tra cách ly dữ liệu
        cls.user_other = cls.env["res.users"].create({
            "name": "Other AI User Conv Test",
            "login": "other_conv_user_test",
            "email": "other_conv_user@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("qba_ai.group_qba_ai_user").id])],
        })

        # 3. Quản trị viên AI
        cls.user_manager = cls.env["res.users"].create({
            "name": "Manager AI User Conv Test",
            "login": "manager_conv_user_test",
            "email": "manager_conv_user@example.com",
            "groups_id": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("qba_ai.group_qba_ai_user").id,
                cls.env.ref("qba_ai.group_qba_ai_manager").id,
            ])],
        })

        # 4. Tạo sản phẩm test để liên kết ngữ cảnh
        cls.product_test = cls.env["product.template"].create({
            "name": "Bánh đà ISUZU 4HF1",
            "default_code": "TEST-FLY-01",
        })

    def test_01_row_button_dispatches_correct_conversation_id(self):
        """01. Nút 'Mở Trợ lý AI' trên dòng trả về đúng client action và conversation_id"""
        conv = self.conv_model.with_user(self.user_test).create({
            "name": "Hội thoại Test Row Button",
            "user_id": self.user_test.id,
            "context_product_id": self.product_test.id,
        })

        action = conv.with_user(self.user_test).action_open_in_drawer()
        self.assertEqual(action.get("type"), "ir.actions.client")
        self.assertEqual(action.get("tag"), "qba_ai_assistant_open")
        self.assertIn("params", action)
        self.assertEqual(action["params"].get("conversation_id"), conv.id)
        self.assertEqual(action["params"].get("product_id"), self.product_test.id)

    def test_02_valid_active_conversation_opens_successfully(self):
        """02. Phiên hội thoại hợp lệ mở thành công với đầy đủ trạng thái và thông tin ngữ cảnh"""
        conv = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên Đang Hoạt Động A",
            "user_id": self.user_test.id,
            "state": "active",
        })

        opened = self.conv_model.with_user(self.user_test).get_or_create_active_conversation(
            conversation_id=conv.id
        )
        self.assertEqual(opened.id, conv.id)
        self.assertTrue(opened.is_active)

        data = opened.get_conversation_data()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("conversation_id"), conv.id)
        self.assertEqual(data.get("name"), "Phiên Đang Hoạt Động A")
        self.assertEqual(data.get("state"), "active")
        self.assertTrue(data.get("is_active"))

    def test_03_archived_conversation_opens_according_to_documented_policy(self):
        """03. Phiên hội thoại đã lưu trữ (archived) vẫn mở được, giữ nguyên lịch sử và trạng thái lưu trữ"""
        conv = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên Đã Lưu Trữ B",
            "user_id": self.user_test.id,
            "state": "archived",
            "is_active": False,
        })
        self.message_model.with_user(self.user_test).create({
            "conversation_id": conv.id,
            "role": "user",
            "content": "Nội dung cũ trong phiên lưu trữ",
        })

        opened = self.conv_model.with_user(self.user_test).get_or_create_active_conversation(
            conversation_id=conv.id
        )
        self.assertEqual(opened.id, conv.id)
        # Theo chính sách: khi mở xem, trạng thái state vẫn là archived cho đến khi khôi phục hoặc gửi tin nhắn mới
        self.assertEqual(opened.state, "archived")

        data = opened.get_conversation_data()
        self.assertEqual(data.get("state"), "archived")
        self.assertEqual(data.get("message_count"), 1)
        self.assertEqual(data["messages"][0]["content"], "Nội dung cũ trong phiên lưu trữ")

    def test_04_selecting_a_then_b_results_in_b_being_active(self):
        """04. Bấm chọn A rồi chọn B thì phiên B trở thành active, phiên A được vô hiệu hóa cờ mở"""
        conv_a = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên Hội Thoại A",
            "user_id": self.user_test.id,
            "state": "active",
        })
        conv_b = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên Hội Thoại B",
            "user_id": self.user_test.id,
            "state": "active",
        })

        # Mở A
        self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv_a.id)
        self.assertTrue(conv_a.is_active)
        self.assertFalse(conv_b.is_active)

        # Mở B
        self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv_b.id)
        conv_a.invalidate_recordset()
        conv_b.invalidate_recordset()
        self.assertFalse(conv_a.is_active, "Phiên A phải bị tắt cờ is_active khi chọn B")
        self.assertTrue(conv_b.is_active, "Phiên B phải được kích hoạt is_active")

    def test_05_rapid_selection_and_idempotent_reselection(self):
        """05. Reselect A -> B -> A liên tiếp hoặc click 2 lần cùng một dòng không gây lỗi và không tạo rác dữ liệu"""
        conv_a = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên A Rapid",
            "user_id": self.user_test.id,
        })
        conv_b = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên B Rapid",
            "user_id": self.user_test.id,
        })

        # Click A 2 lần
        self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv_a.id)
        self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv_a.id)
        self.assertTrue(conv_a.is_active)

        # Chuyển A -> B -> A
        self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv_b.id)
        self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv_a.id)

        conv_a.invalidate_recordset()
        conv_b.invalidate_recordset()
        self.assertTrue(conv_a.is_active)
        self.assertFalse(conv_b.is_active)

    def test_06_missing_or_inaccessible_id_raises_error_not_silent_fallback(self):
        """06. ID không tồn tại hoặc ID của người dùng khác phải báo lỗi tường minh, KHÔNG âm thầm nạp bừa phiên khác"""
        # 1. ID không tồn tại
        with self.assertRaises(ValidationError):
            self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=99999999)

        # 2. ID thuộc sở hữu của User Other -> User Test không được mở
        conv_other = self.conv_model.with_user(self.user_other).create({
            "name": "Hội thoại bảo mật của Other",
            "user_id": self.user_other.id,
        })
        with self.assertRaises(AccessError):
            self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv_other.id)

    def test_07_failed_request_does_not_corrupt_current_valid_conversation(self):
        """07. Khi một yêu cầu mở thất bại (ID sai), phiên hợp lệ hiện tại vẫn được bảo toàn nguyên vẹn"""
        conv_current = self.conv_model.with_user(self.user_test).create({
            "name": "Hội thoại Hiện Tại Hợp Lệ",
            "user_id": self.user_test.id,
            "is_active": True,
        })

        # Giả lập gọi backend với ID lỗi
        try:
            self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=88888888)
        except ValidationError:
            pass

        conv_current.invalidate_recordset()
        self.assertTrue(conv_current.is_active, "Phiên hợp lệ ban đầu không được bị hủy hoại khi có request lỗi")

    def test_08_follow_up_messages_saved_to_selected_conversation(self):
        """08. Tin nhắn tiếp theo được lưu đúng vào phiên hội thoại đang chọn, không ghi nhầm sang phiên khác"""
        conv_1 = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên 1 Tra Cứu",
            "user_id": self.user_test.id,
        })
        conv_2 = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên 2 Tra Cứu",
            "user_id": self.user_test.id,
        })

        # Mở phiên 2 và gửi tin nhắn
        self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv_2.id)
        conv_2.post_user_message("Tin nhắn riêng cho phiên 2")

        self.assertEqual(len(conv_1.message_ids), 0)
        self.assertGreater(len(conv_2.message_ids), 0)
        self.assertIn("Tin nhắn riêng cho phiên 2", [m.content for m in conv_2.message_ids])

    def test_09_floating_launcher_canonical_session_rules(self):
        """09. Launcher nổi tuân thủ quy tắc chuẩn: mở lại phiên active hiện có, không tạo phiên trùng lặp"""
        conv_exist = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên Đang Chạy Sẵn",
            "user_id": self.user_test.id,
            "is_active": True,
            "state": "active",
        })

        # Launcher mở không truyền conversation_id
        opened = self.conv_model.with_user(self.user_test).get_or_create_active_conversation()
        self.assertEqual(opened.id, conv_exist.id, "Launcher nổi phải tái sử dụng đúng phiên đang mở")

    def test_10_opening_existing_session_never_creates_duplicate(self):
        """10. Mở một phiên đã có không bao giờ sinh ra thêm bản ghi hội thoại mới"""
        conv = self.conv_model.with_user(self.user_test).create({
            "name": "Kiểm tra Chống Nhân Bản",
            "user_id": self.user_test.id,
        })

        count_before = self.conv_model.with_user(self.user_test).search_count([("user_id", "=", self.user_test.id)])

        for _ in range(5):
            self.conv_model.with_user(self.user_test).get_or_create_active_conversation(conversation_id=conv.id)

        count_after = self.conv_model.with_user(self.user_test).search_count([("user_id", "=", self.user_test.id)])
        self.assertEqual(count_before, count_after, "Số lượng hội thoại không được tăng khi chỉ mở xem")

    def test_11_unauthorized_user_cannot_open_another_users_conversation(self):
        """11. Người dùng thông thường không thể mở phiên hội thoại của người khác qua action_open_in_drawer"""
        conv_other = self.conv_model.with_user(self.user_other).create({
            "name": "Bí mật kinh doanh của User Other",
            "user_id": self.user_other.id,
        })

        with self.assertRaises(AccessError):
            conv_other.with_user(self.user_test).action_open_in_drawer()

    def test_12_archive_and_restore_preserve_entire_history(self):
        """12. Lưu trữ và Khôi phục bảo toàn 100% lịch sử tin nhắn theo thứ tự thời gian"""
        conv = self.conv_model.with_user(self.user_test).create({
            "name": "Phiên Lưu Trữ Và Khôi Phục",
            "user_id": self.user_test.id,
            "state": "active",
        })

        # Tạo chuỗi tin nhắn
        for i in range(4):
            self.message_model.with_user(self.user_test).create({
                "conversation_id": conv.id,
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Tin nhắn kiểm thử thứ {i}",
            })

        self.assertEqual(conv.message_count, 4)

        # 1. Lưu trữ
        conv.action_archive()
        self.assertEqual(conv.state, "archived")
        self.assertFalse(conv.is_active)
        self.assertEqual(conv.message_count, 4)

        # 2. Khôi phục
        conv.action_restore()
        self.assertEqual(conv.state, "active")
        self.assertEqual(conv.message_count, 4)

        # Kiểm tra thứ tự và nội dung tin nhắn
        msgs = conv.message_ids.sorted('id')
        for i, m in enumerate(msgs):
            self.assertEqual(m.content, f"Tin nhắn kiểm thử thứ {i}")

