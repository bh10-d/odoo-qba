# -*- coding: utf-8 -*-
import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class QbaSpecParserRegistry(models.AbstractModel):
    _name = "qba.spec.parser.registry"
    _description = "Bộ Đăng Ký & Điều Hướng Parser Thông Số Kỹ Thuật (Specification Parser Registry)"

    # Danh sách các implementation model đã đăng ký trong hệ thống
    # Mỗi implementation cung cấp các phương thức:
    # - is_category_supported(category) -> bool
    # - open_product_wizard(product) -> dict (ir.actions.act_window)
    # - open_category_wizard(category) -> dict (ir.actions.act_window)
    _parser_models = ["qba.lc.spec.parser"]

    @api.model
    def register_parser_model(self, model_name):
        """Đăng ký động một parser implementation model mới vào registry."""
        if model_name not in self._parser_models:
            self._parser_models.append(model_name)

    @api.model
    def get_parser_for_category(self, category):
        """Tra cứu parser implementation phù hợp cho danh mục sản phẩm.
        Hoàn toàn KHÔNG hardcode mã hay tên danh mục cụ thể ở tầng Dispatcher này.
        Từng implementation tự chịu trách nhiệm thẩm định xem danh mục có thuộc phạm vi hỗ trợ hay không.
        """
        if not category:
            return False

        for model_name in self._parser_models:
            if model_name in self.env:
                parser_model = self.env[model_name]
                if hasattr(parser_model, "is_category_supported"):
                    try:
                        if parser_model.is_category_supported(category):
                            return parser_model
                    except Exception as e:
                        _logger.error("Lỗi khi kiểm tra parser %s cho danh mục %s: %s", model_name, category.display_name, e)
        return False

    @api.model
    def open_product_wizard(self, product):
        """Điều hướng mở wizard trích xuất thông số cho sản phẩm qua parser tương ứng."""
        parser = self.get_parser_for_category(product.categ_id)
        if parser is False:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Chưa hỗ trợ công cụ trích xuất"),
                    "message": _("Danh mục '%(category)s' hiện chưa có bộ trích xuất thông số kỹ thuật tự động.") % {
                        "category": product.categ_id.display_name if product.categ_id else _("Chưa phân loại"),
                    },
                    "type": "warning",
                    "sticky": False,
                },
            }
        return parser.open_product_wizard(product)

    @api.model
    def open_category_wizard(self, category):
        """Điều hướng mở wizard trích xuất thông số cho danh mục qua parser tương ứng."""
        parser = self.get_parser_for_category(category)
        if parser is False:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Chưa hỗ trợ công cụ trích xuất"),
                    "message": _("Danh mục '%(category)s' hiện chưa có bộ trích xuất thông số kỹ thuật tự động.") % {
                        "category": category.display_name if category else _("Chưa phân loại"),
                    },
                    "type": "warning",
                    "sticky": False,
                },
            }
        return parser.open_category_wizard(category)

