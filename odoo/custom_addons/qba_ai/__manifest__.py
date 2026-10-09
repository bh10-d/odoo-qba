# -*- coding: utf-8 -*-
{
    "name": "QBA AI - Tra Cứu Phụ Tùng & Đo Lường",
    "summary": "Tích hợp Gemini AI trợ giúp nhân viên tra cứu cách đo phụ tùng, tìm sản phẩm và quản lý hàng chờ Admin duyệt",
    "description": """
        Module QBA AI bao gồm:
        - Tích hợp Gemini API với cơ chế Cache & Chống quá tải Request.
        - Quản lý Thư viện Kiến thức & Hướng dẫn đo phụ tùng.
        - Trợ lý AI tra cứu sản phẩm theo kích thước / thông số kỹ thuật.
        - Hàng chờ Admin phê duyệt kiến thức (Human-in-the-loop).
    """,
    "version": "1.0",
    "category": "Inventory/Technical",
    "author": "FACT",
    "depends": ["base", "product", "stock", "qba"],
    "data": [
        "security/ir.model.access.csv",
        "data/default_data.xml",
        "views/ai_knowledge_views.xml",
        "views/ai_approval_queue_views.xml",
        "views/ai_assistant_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
