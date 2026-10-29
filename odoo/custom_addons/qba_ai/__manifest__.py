# -*- coding: utf-8 -*-
{
    "name": "QBA AI - Tra Cứu Phụ Tùng & Đo Lường",
    "summary": "Tích hợp Gemini AI trợ giúp nhân viên tra cứu cách đo phụ tùng, tìm sản phẩm và quản lý hàng chờ Admin duyệt",
    "description": """
        Module QBA AI bao gồm:
        - Tích hợp Gemini API với cơ chế Cache & Chống quá tải Request.
        - Quản lý Thư viện Kiến thức & Hướng dẫn đo phụ tùng.
        - Quản lý Thông số kỹ thuật động (Dynamic Technical Specifications).
        - Trợ lý AI tra cứu sản phẩm theo kích thước / thông số kỹ thuật.
        - Hàng chờ Admin phê duyệt kiến thức & thông số kỹ thuật (Human-in-the-loop).
    """,
    "version": "1.0",
    "category": "Inventory/Technical",
    "author": "FACT",
    "depends": ["base", "product", "stock", "qba", "mail"],
    "data": [
        "security/qba_ai_security.xml",
        "security/ir.model.access.csv",
        "data/default_data.xml",
        "views/product_spec_definition_views.xml",
        "views/product_spec_value_views.xml",
        "views/product_category_views.xml",
        "views/product_template_views.xml",
        "views/ai_knowledge_views.xml",
        "views/ai_approval_queue_views.xml",
        "views/ai_request_views.xml",
        "views/ai_assistant_views.xml",
        "views/ai_conversation_views.xml",
        "views/res_config_settings_views.xml",
        "views/lc_spec_parser_views.xml",
        "views/category_matching_profile_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "qba_ai/static/src/css/technical_specs.css",
            "qba_ai/static/src/css/ai_assistant_drawer.css",
            "qba_ai/static/src/js/ai_assistant_drawer.js",
            "qba_ai/static/src/xml/ai_assistant_drawer.xml",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
