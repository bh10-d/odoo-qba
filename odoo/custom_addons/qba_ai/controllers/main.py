import json
import logging
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError

_logger = logging.getLogger(__name__)


class QbaAiAssistantController(http.Controller):

    @http.route("/qba_ai/conversation/get_active", type="json", auth="user")
    def get_active_conversation(self, context_product_id=None, conversation_id=None):
        """Lấy phiên hội thoại hiện tại, hoặc nạp theo conversation_id, hoặc tạo mới nếu chưa có."""
        try:
            conv_model = request.env["qba.ai.conversation"]
            conv = conv_model.get_or_create_active_conversation(
                context_product_id=context_product_id,
                conversation_id=conversation_id
            )
            return {
                "success": True,
                "data": conv.get_conversation_data()
            }
        except (AccessError, ValidationError, UserError) as e:
            return {"success": False, "error": str(e.name if hasattr(e, "name") else e)}
        except Exception as e:
            _logger.error("Lỗi get_active_conversation: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/get_history", type="json", auth="user")
    def get_conversation_history(self, limit=30):
        """Lấy danh sách các cuộc hội thoại trước đó của người dùng."""
        try:
            conv_model = request.env["qba.ai.conversation"]
            history = conv_model.get_user_conversations_history(limit=limit)
            return {"success": True, "data": history}
        except Exception as e:
            _logger.error("Lỗi get_conversation_history: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/load", type="json", auth="user")
    def load_conversation(self, conversation_id):
        """Nạp một phiên hội thoại cụ thể từ lịch sử và đặt làm phiên active."""
        try:
            conv = request.env["qba.ai.conversation"].browse(int(conversation_id)).exists()
            if not conv:
                return {"success": False, "error": _("Phiên hội thoại không tồn tại.")}
            conv.check_access('read')
            if conv.user_id != request.env.user and not request.env.user.has_group("qba_ai.group_qba_ai_manager"):
                return {"success": False, "error": _("Bạn không có quyền truy cập phiên hội thoại của người dùng khác.")}
            request.env["qba.ai.conversation"].search([
                ("user_id", "=", request.env.user.id),
                ("id", "!=", conv.id),
                ("is_active", "=", True)
            ]).write({"is_active": False})
            if conv.user_id == request.env.user:
                conv.write({"is_active": True})
            return {"success": True, "data": conv.get_conversation_data()}
        except (AccessError, ValidationError, UserError) as e:
            return {"success": False, "error": str(e.name if hasattr(e, "name") else e)}
        except Exception as e:
            _logger.error("Lỗi load_conversation: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/restore", type="json", auth="user")
    def restore_conversation(self, conversation_id):
        """Khôi phục phiên hội thoại từ trạng thái lưu trữ về đang hoạt động."""
        try:
            conv = request.env["qba.ai.conversation"].browse(int(conversation_id)).exists()
            if not conv:
                return {"success": False, "error": _("Phiên hội thoại không tồn tại.")}
            conv.check_access('write')
            conv.action_restore()
            return {"success": True, "data": conv.get_conversation_data()}
        except (AccessError, ValidationError, UserError) as e:
            return {"success": False, "error": str(e.name if hasattr(e, "name") else e)}
        except Exception as e:
            _logger.error("Lỗi restore_conversation: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/archive", type="json", auth="user")
    def archive_conversation(self, conversation_id):
        """Lưu trữ một phiên hội thoại."""
        try:
            conv = request.env["qba.ai.conversation"].browse(int(conversation_id)).exists()
            if not conv:
                return {"success": False, "error": _("Phiên hội thoại không tồn tại.")}
            conv.check_access('write')
            conv.action_archive()
            return {"success": True, "data": conv.get_conversation_data()}
        except (AccessError, ValidationError, UserError) as e:
            return {"success": False, "error": str(e.name if hasattr(e, "name") else e)}
        except Exception as e:
            _logger.error("Lỗi archive_conversation: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/send_message", type="json", auth="user")
    def send_message(self, conversation_id, content, context_product_id=None):
        """Gửi tin nhắn từ người dùng và nhận kết quả phản hồi đàm thoại có cấu trúc."""
        try:
            conv = request.env["qba.ai.conversation"].browse(int(conversation_id)).exists()
            if not conv:
                return {"success": False, "error": _("Phiên hội thoại không tồn tại.")}
            conv.check_access('write')
            # Nếu gửi tin nhắn vào hội thoại đang lưu trữ, tự động kích hoạt lại trạng thái hoạt động
            if conv.state == "archived":
                conv.write({"state": "active"})
            
            # Kiểm tra phân quyền truy cập
            conv.check_access('write')
            conv.post_user_message(content, context_product_id=context_product_id)
            return {"success": True, "data": conv.get_conversation_data()}
        except Exception as e:
            _logger.error("Lỗi send_message: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/new", type="json", auth="user")
    def new_conversation(self, context_product_id=None):
        """Bắt đầu phiên hội thoại mới sạch sẽ."""
        try:
            conv_model = request.env["qba.ai.conversation"]
            conv = conv_model.create_new_conversation(context_product_id=context_product_id)
            return {"success": True, "data": conv.get_conversation_data()}
        except Exception as e:
            _logger.error("Lỗi new_conversation: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/clear_product", type="json", auth="user")
    def clear_context_product(self, conversation_id):
        """Xóa sản phẩm ngữ cảnh khỏi phiên hội thoại để tìm kiếm chung."""
        try:
            conv = request.env["qba.ai.conversation"].browse(int(conversation_id)).exists()
            if not conv:
                return {"success": False, "error": _("Phiên hội thoại không tồn tại.")}
            conv.clear_context_product()
            return {"success": True, "data": conv.get_conversation_data()}
        except Exception as e:
            _logger.error("Lỗi clear_context_product: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/set_product", type="json", auth="user")
    def set_context_product(self, conversation_id, product_id):
        """Gán sản phẩm ngữ cảnh cho phiên hội thoại."""
        try:
            conv = request.env["qba.ai.conversation"].browse(int(conversation_id)).exists()
            if not conv:
                return {"success": False, "error": _("Phiên hội thoại không tồn tại.")}
            data = conv.set_context_product(product_id)
            return {"success": True, "data": data}
        except Exception as e:
            _logger.error("Lỗi set_context_product: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/conversation/delete", type="json", auth="user")
    def delete_conversation(self, conversation_id):
        """Xóa vĩnh viễn một cuộc hội thoại."""
        try:
            conv = request.env["qba.ai.conversation"].browse(int(conversation_id)).exists()
            if not conv:
                return {"success": False, "error": _("Phiên hội thoại không tồn tại.")}
            conv.check_access('unlink')
            conv.unlink()
            return {"success": True}
        except Exception as e:
            _logger.error("Lỗi delete_conversation: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/request/submit", type="json", auth="user")
    def submit_ai_request(self, conversation_id=None, message_id=None, request_type="missing_product",
                          raw_query="", product_id=None, extracted_specs=None, user_notes=None):
        """Tiếp nhận yêu cầu từ Trợ lý QBA AI Drawer gửi đến Admin."""
        try:
            conv = None
            if conversation_id:
                conv = request.env["qba.ai.conversation"].browse(int(conversation_id)).exists()
                if not conv:
                    return {"success": False, "error": _("Phiên hội thoại không tồn tại.")}
                conv.check_access('read')

            msg = None
            if message_id:
                msg = request.env["qba.ai.message"].browse(int(message_id)).exists()
                if msg:
                    msg.check_access('read')
                    if msg.conversation_id and msg.conversation_id.user_id != request.env.user and not request.env.user.has_group("qba_ai.group_qba_ai_manager"):
                        return {"success": False, "error": _("Bạn không có quyền truy cập tin nhắn này.")}

            # Chuyển extracted_specs thành JSON string nếu là dict/list
            specs_json = ""
            if extracted_specs:
                if isinstance(extracted_specs, (dict, list)):
                    specs_json = json.dumps(extracted_specs, ensure_ascii=False)
                else:
                    specs_json = str(extracted_specs)

            vals = {
                "request_type": request_type,
                "raw_query": (raw_query or "").strip(),
                "conversation_id": conv.id if conv else False,
                "message_id": msg.id if msg else False,
                "product_id": int(product_id) if product_id else False,
                "extracted_specs_json": specs_json,
                "user_notes": (user_notes or "").strip(),
                "state": "submitted",
            }

            req = request.env["qba.ai.request"].create_from_drawer(vals)

            return {
                "success": True,
                "data": {
                    "request_id": req.id,
                    "request_name": req.name,
                    "request_type": req.request_type,
                    "state": req.state,
                    "conversation_data": conv.get_conversation_data() if conv else None,
                }
            }
        except ValidationError as e:
            return {"success": False, "error": str(e)}
        except AccessError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            _logger.error("Lỗi submit_ai_request: %s", e)
            return {"success": False, "error": str(e)}

    @http.route("/qba_ai/request/get_user_requests", type="json", auth="user")
    def get_user_requests(self, limit=20):
        """Lấy danh sách các yêu cầu của người dùng hiện tại."""
        try:
            reqs = request.env["qba.ai.request"].search([
                ("user_id", "=", request.env.user.id)
            ], limit=limit, order="create_date desc")
            data = [{
                "id": r.id,
                "name": r.name,
                "request_type": r.request_type,
                "request_type_label": dict(r._fields['request_type'].selection).get(r.request_type, r.request_type),
                "state": r.state,
                "state_label": dict(r._fields['state'].selection).get(r.state, r.state),
                "raw_query": r.raw_query,
                "product_name": r.product_id.name if r.product_id else "",
                "product_code": r.product_id.default_code if r.product_id else "",
                "create_date": fields.Datetime.to_string(r.create_date),
                "admin_feedback": r.admin_feedback or "",
                "rejection_reason": r.rejection_reason or "",
                "handler_name": r.handler_id.name if r.handler_id else "",
            } for r in reqs]
            return {"success": True, "data": data}
        except Exception as e:
            _logger.error("Lỗi get_user_requests: %s", e)
            return {"success": False, "error": str(e)}
