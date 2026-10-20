# -*- coding: utf-8 -*-
import re
import logging
from odoo import models, api, _
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)


class QbaQueryIntentRouter(models.AbstractModel):
    _name = "qba.query.intent.router"
    _description = "Bộ Điều Hướng & Nhận Diện Ý Định Truy Vấn Đa Danh Mục (Generic Intent Router)"

    # Từ khóa định danh thay thế / tương thích
    REPLACEMENT_KEYWORDS = [
        r'thay\s+thế\s+(?:cho\s+)?',
        r'thay\s+cho\s+',
        r'tương\s+đương\s+(?:với\s+)?',
        r'phụ\s+tùng\s+thay\s+(?:thế\s+)?',
        r'mã\s+thay\s+(?:thế\s+)?',
        r'thay\s+được\s+(?:cho\s+)?',
        r'lắp\s+thay\s+(?:cho\s+)?',
        r'substitute\s+(?:for\s+)?',
        r'replace(?:ment)?\s+(?:for\s+)?',
        r'compatible\s+with\s+',
    ]

    # Nhận diện bối cảnh thiết bị / xe / động cơ / hộp số phổ biến của QBA
    EQUIPMENT_PATTERNS = [
        # Dòng xe tải / đầu kéo
        r'\b(?:howo|sinotruk|dongfeng|chenglong|shacman|auman|thaco|ollin|foton|hino|isuzu|hyundai|camc|jac|faw)\b',
        # Dòng động cơ
        r'\b(?:weichai|yuchai|cummins|shangchai|wp10|wp12|wp7|yc6l|yc6a|yc4d|mc07|mc11|d10|d12|wd615)\b',
        # Dòng hộp số
        r'\b(?:fast\s+gear|8js85t|9js119|10jsd|12jsd|16jsd|hw19710|hw18709|hw19712)\b',
        # Loại tải trọng / xe
        r'\b(?:xe\s+ben|xe\s+đầu\s+kéo|xe\s+tải|xe\s+trộn\s+bê\s+tông|mooc)\b',
    ]

    # Stop words tiếng Việt cần loại bỏ khi trích xuất từ khóa cốt lõi
    STOP_WORDS = {
        'hãy', 'hay', 'hướng', 'huong', 'dẫn', 'dan', 'chi', 'tiết', 'tiet', 'quy', 'trình', 'trinh',
        'kiểm', 'kiem', 'tra', 'và', 'va', 'đo', 'do', 'đạc', 'dac', 'kỹ', 'ky', 'thuật', 'thuat',
        'trước', 'truoc', 'khi', 'thay', 'thế', 'the', 'cho', 'khong', 'không', 'co', 'có', 'anh',
        'toi', 'tôi', 'ban', 'bạn', 'em', 'loai', 'loại', 'tim', 'tìm', 'giup', 'giúp',
        'xem', 'duoc', 'được', 'nao', 'nào', 'voi', 'với', 'trong', 'kho', 'hoi', 'hỏi', 'thi', 'thì',
        'về', 've', 'của', 'cua', 'đang', 'dang', 'lại', 'lai', 'ở', 'tại', 'nay', 'quả', 'qua',
        'cái', 'cai', 'chiếc', 'chiec', 'gì', 'gi', 'này', 'nay', 'giá', 'gia', 'bao', 'nhiêu', 'nhieu',
        'alo', 'a-lô', 'hello', 'hi', 'chào', 'chao', 'xin', 'ơi', 'oi', 'dạ', 'da', 'vâng', 'vang'
    }

    @api.model
    def route_query(self, query, context_category=None):
        """Phân tích chuỗi truy vấn người dùng và định tuyến sang Intent chính xác.
        Hỗ trợ 7 loại ý định (Generic Intent Types) hoàn toàn không hardcode danh mục LC:
        1. exact_sku: Tra cứu SKU / mã sản phẩm chính xác.
        2. explicit_replacement: Yêu cầu tìm phụ tùng thay thế cho một sản phẩm cơ sở.
        3. technical_spec_only: Tra cứu thuần thông số kỹ thuật (ví dụ kích thước, đường kính, số răng...).
        4. equipment_context: Tra cứu theo bối cảnh xe, động cơ, hộp số hoặc dòng máy.
        5. product_name_alias: Tra cứu theo tên hoặc bí danh phụ tùng.
        6. natural_language_description: Mô tả tự nhiên về phụ tùng.
        7. ambiguous: Truy vấn mơ hồ, quá ngắn hoặc không đủ thông tin.
        """
        raw_query = (query or "").strip()
        if not raw_query:
            return self._build_router_result(
                intent="ambiguous",
                label=_("Truy vấn rỗng"),
                query=raw_query,
                is_ambiguous=True,
                clarification=_("Vui lòng nhập mã sản phẩm, tên phụ tùng hoặc thông số kỹ thuật cần tra cứu.")
            )

        # A. Kiểm tra Intent 5: Explicit Replacement (Tìm phụ tùng thay thế)
        is_repl, repl_target_str = self._detect_replacement_intent(raw_query)
        if is_repl:
            base_prod, base_sku = self._resolve_product_by_code_or_name(repl_target_str or raw_query)
            category = base_prod.categ_id if base_prod else self._detect_category(raw_query)
            return self._build_router_result(
                intent="explicit_replacement",
                label=_("Tra cứu phụ tùng thay thế"),
                query=raw_query,
                target_sku=base_sku,
                target_product=base_prod,
                target_category=category,
                clean_query=repl_target_str,
            )

        # B. Kiểm tra Intent 1: Exact SKU Lookup (Tìm chính xác theo mã SKU / default_code)
        sku_prod, sku_code = self._detect_exact_sku(raw_query)
        if sku_prod:
            return self._build_router_result(
                intent="exact_sku",
                label=_("Tra cứu mã SKU chính xác"),
                query=raw_query,
                target_sku=sku_code,
                target_product=sku_prod,
                target_category=sku_prod.categ_id,
            )

        # C. Kiểm tra Intent 4: Technical Spec Only (Tra cứu theo thông số kỹ thuật)
        detected_category = self._detect_category(raw_query) or context_category
        extracted_specs, unresolved_numerics, inferred_cat = self._extract_technical_specs(
            raw_query, category=detected_category, return_details=True
        )
        if inferred_cat and not detected_category:
            detected_category = inferred_cat
        if extracted_specs:
            return self._build_router_result(
                intent="technical_spec_only",
                label=_("Tra cứu theo thông số kỹ thuật"),
                query=raw_query,
                target_category=detected_category,
                extracted_specs=extracted_specs,
                unresolved_numerics=unresolved_numerics,
            )

        # C.2 Nếu chưa nhận diện được spec nào nhưng có số chưa phân giải (Unresolved Numerics)
        # CHỈ kích hoạt ambiguous nếu truy vấn ngắn (dưới 4 từ có nghĩa), ví dụ: '325', '123'
        # Nếu là câu hỏi đàm thoại dài -> chuyển tiếp sang intent mô tả tự nhiên / AI
        clean_tokens = self._extract_clean_tokens(raw_query)
        if unresolved_numerics and not extracted_specs and not self._detect_equipment_context(raw_query) and len(clean_tokens) <= 3:
            nums_str = ", ".join(str(int(n) if n == int(n) else n) for n in unresolved_numerics)
            clarification = _(
                "Hệ thống ghi nhận con số: %s nhưng chưa rõ đây là thông số kỹ thuật nào "
                "(ví dụ: đường kính ngoài, số răng, hay mã phụ tùng). Vui lòng bổ sung loại phụ tùng "
                "(lá côn, tăm bua, v.v.) hoặc tên thông số cụ thể."
            ) % nums_str
            return self._build_router_result(
                intent="ambiguous",
                label=_("Yêu cầu chưa rõ ràng"),
                query=raw_query,
                is_ambiguous=True,
                unresolved_numerics=unresolved_numerics,
                clarification=clarification,
            )

        # D. Kiểm tra Intent 6: Equipment Context (Tra cứu theo model xe / động cơ)
        equipment_terms = self._detect_equipment_context(raw_query)
        if equipment_terms:
            return self._build_router_result(
                intent="equipment_context",
                label=_("Tra cứu theo thiết bị / động cơ"),
                query=raw_query,
                target_category=detected_category,
                equipment_terms=equipment_terms,
            )

        # E. Kiểm tra Intent 7: Ambiguous / Quá ngắn / Không rõ ý định
        if self._is_ambiguous_query(raw_query):
            return self._build_router_result(
                intent="ambiguous",
                label=_("Yêu cầu chưa rõ ràng"),
                query=raw_query,
                is_ambiguous=True,
                clarification=_("Truy vấn quá ngắn hoặc chưa rõ ràng. Bạn có thể tra cứu theo mã SKU (ví dụ: LC.002, TBUA.010, BN-005), theo thông số kỹ thuật, hoặc tên phụ tùng kèm dòng xe.")
            )

        # F. Kiểm tra Intent 2 & 3: Product Name Alias hoặc Natural Language Description
        clean_tokens = self._extract_clean_tokens(raw_query)
        if len(clean_tokens) <= 3 and detected_category:
            return self._build_router_result(
                intent="product_name_alias",
                label=_("Tra cứu tên / danh mục phụ tùng"),
                query=raw_query,
                target_category=detected_category,
                clean_terms=clean_tokens,
            )

        return self._build_router_result(
            intent="natural_language_description",
            label=_("Tìm kiếm theo mô tả phụ tùng"),
            query=raw_query,
            target_category=detected_category,
            clean_terms=clean_tokens,
        )

    # =========================================================================
    # PHƯƠNG THỨC NHẬN DIỆN CHI TIẾT TỪNG Ý ĐỊNH (ĐỘC LẬP & DỄ KIỂM THỬ)
    # =========================================================================

    @api.model
    def _detect_exact_sku(self, query):
        """Phát hiện nếu chuỗi truy vấn trùng khớp mã SKU/default_code/brand_sku của sản phẩm"""
        clean_q = query.strip()
        # Loại bỏ các tiền tố như "mã:", "sku:", "code:", hoặc các tiền tố so sánh "so sánh với"
        clean_q = re.sub(
            r'^(?:so\s+sánh\s+(?:với\s+)?|đối\s+chiếu\s+(?:với\s+)?|so\s+với\s+|mã\s*[:=]?\s*|sku\s*[:=]?\s*|code\s*[:=]?\s*|part\s*no\.?\s*[:=]?\s*)',
            '', clean_q, flags=re.I
        ).strip()

        # Kiểm tra exact match với default_code, brand_sku hoặc barcode
        prod = self.env['product.template'].search([
            '|', '|',
            ('default_code', '=ilike', clean_q),
            ('brand_sku', '=ilike', clean_q),
            ('barcode', '=ilike', clean_q),
        ], limit=1)
        if prod:
            return (prod, clean_q)

        # Kiểm tra pattern mã kỹ thuật chuẩn (chữ + số + dấu chấm/gạch ngang)
        model_pattern = r'^[A-Za-z0-9]+[A-Za-z0-9\.-]{2,}$'
        if re.match(model_pattern, clean_q) and not re.search(r'\s', clean_q):
            # Thử tìm kiếm exact trên name hoặc default_code
            prod_prefix = self.env['product.template'].search([
                '|',
                ('default_code', '=ilike', clean_q),
                ('name', '=ilike', clean_q),
            ], limit=1)
            if prod_prefix:
                return (prod_prefix, clean_q)

        # Tìm token SKU kỹ thuật nằm bên trong câu hỏi (ví dụ: "So sánh với LC.002")
        for m_sku in re.finditer(r'\b([A-Za-z0-9]+[\.-][A-Za-z0-9\.-]+)\b', query):
            embedded_code = m_sku.group(1).strip()
            prod_embedded = self.env['product.template'].search([
                '|', '|',
                ('default_code', '=ilike', embedded_code),
                ('brand_sku', '=ilike', embedded_code),
                ('barcode', '=ilike', embedded_code),
            ], limit=1)
            if prod_embedded:
                return (prod_embedded, embedded_code)

        return (False, False)

    @api.model
    def _detect_replacement_intent(self, query):
        """Phát hiện ý định tìm phụ tùng thay thế (Explicit Replacement Search)"""
        for pat in self.REPLACEMENT_KEYWORDS:
            match = re.search(pat, query, re.I)
            if match:
                remainder = query[match.end():].strip()
                remainder = re.sub(r'^(?:cho\s+)?(?:mã\s+|sản\s+phẩm\s+|sp\s+)?', '', remainder, flags=re.I).strip()
                if re.match(r'^(?:không|ko|nào\s+không|nào\s+ko)\??$', remainder, re.I):
                    remainder = ""
                return (True, remainder or query)
        return (False, None)

    @api.model
    def _detect_equipment_context(self, query):
        """Trích xuất các thực thể bối cảnh thiết bị, dòng xe hoặc động cơ trong câu hỏi"""
        found = []
        for pat in self.EQUIPMENT_PATTERNS:
            matches = re.findall(pat, query, re.I)
            for m in matches:
                clean_m = m.strip().upper()
                if clean_m not in found:
                    found.append(clean_m)
        return found

    @api.model
    def _detect_category(self, query):
        """Nhận diện danh mục sản phẩm từ chuỗi câu hỏi dựa trên CSDL product.category thực tế.
        Hoàn toàn KHÔNG hardcode danh mục LC làm mặc định.
        Sử dụng phân tích cú pháp tiếng Việt (Head Noun Priority):
        1. Trích xuất mã danh mục chính xác từ tiền tố (ví dụ 'BI+' -> 'bi+', 'BI' -> 'bi', 'LC' -> 'lc').
           Không để 'BI+' bị cắt mất ký tự '+' dẫn đến nhận diện nhầm sang 'BI'.
        2. Nhận diện các danh từ / cụm từ danh mục và từ đồng nghĩa ngành phụ tùng xe tải.
        3. Ưu tiên danh từ đứng đầu câu (Head Noun): Trong tiếng Việt, danh từ chính đứng trước, định ngữ đứng sau.
           Ví dụ: 'vòng bi moay ơ' -> danh từ chính là 'vòng bi' (BI), 'moay ơ' là định ngữ -> Danh mục BI.
                  'moay ơ sau' -> danh từ chính là 'moay ơ' -> Danh mục MO.
        """
        all_cats = self.env['product.category'].search([])
        q_lower = query.lower()

        best_cat = False
        best_score = 0

        for cat in all_cats:
            raw_name = cat.name or ''
            m = re.match(r'^([A-Z0-9\+]+)\s*[-–]\s*(.+)$', raw_name)
            code = m.group(1).strip() if m else None
            title = m.group(2).strip() if m else raw_name.strip()

            # Các từ đồng nghĩa kỹ thuật phổ biến theo mã danh mục thực tế
            synonyms = []
            if code == 'BI' or 'bi các loại' in title.lower():
                synonyms.extend(['vòng bi', 'bạc đạn', 'bi', 'ổ bi'])
            elif code == 'BEP' or 'bàn ép' in title.lower():
                synonyms.extend(['bàn ép', 'mâm ép'])
            elif code == 'LC' or 'lá côn' in title.lower():
                synonyms.extend(['lá côn', 'đĩa ly hợp', 'bố ly hợp'])
            elif code == 'TBUA' or 'tăm bua' in title.lower():
                synonyms.extend(['tăm bua', 'tambua', 'tam bua', 'trống phanh'])
            elif code == 'MO' or 'moay ơ' in title.lower():
                synonyms.extend(['moay ơ', 'moayo', 'mayơ', 'đùm bánh'])

            score = 0
            first_pos = 999

            # 1. Khớp mã danh mục chính xác (ví dụ LC, BI, BI+, TBUA)
            if code:
                code_lower = code.lower()
                if '+' in code_lower:
                    pat = r'(?:\b|\A)' + re.escape(code_lower) + r'(?:\b|\Z|\s)'
                else:
                    pat = r'\b' + re.escape(code_lower) + r'\b'
                m_code = re.search(pat, q_lower)
                if m_code:
                    score = max(score, 80 + len(code_lower))
                    first_pos = min(first_pos, m_code.start())

            # 2. Khớp cụm tên danh mục đầy đủ
            if title and len(title) >= 3:
                m_title = re.search(r'\b' + re.escape(title.lower()) + r'\b', q_lower)
                if m_title:
                    score = max(score, 100 + len(title))
                    first_pos = min(first_pos, m_title.start())

            # 3. Khớp từng phần của tên danh mục
            parts = [p.strip().lower() for p in re.split(r'[-–/(),]', title) if len(p.strip()) >= 3]
            for p in parts:
                # Bỏ qua nếu từ này đi liền sau số đo thông số (ví dụ: '8 lò xo', '10 răng', '10 lỗ')
                if re.search(r'\b\d+(?:[.,]\d+)?\s*' + re.escape(p) + r'\b', q_lower):
                    continue
                m_part = re.search(r'\b' + re.escape(p) + r'\b', q_lower)
                if m_part:
                    score = max(score, 70 + len(p))
                    first_pos = min(first_pos, m_part.start())

            # 4. Khớp từ đồng nghĩa
            for s in synonyms:
                m_syn = re.search(r'\b' + re.escape(s) + r'\b', q_lower)
                if m_syn:
                    score = max(score, 90 + len(s))
                    first_pos = min(first_pos, m_syn.start())

            # Ưu tiên Head Noun (từ xuất hiện trước trong ngữ cảnh tiếng Việt)
            final_score = score - (first_pos * 5) if score > 0 else 0
            if final_score > best_score:
                best_score = final_score
                best_cat = cat

        return best_cat

    @api.model
    def _extract_technical_specs(self, query, category=None, return_details=False):
        """Trích xuất thông số kỹ thuật đa danh mục dựa trên định nghĩa CSDL (Data-Driven).
        1. Thu thập vị trí toàn bộ các token số xuất hiện trong chuỗi.
        2. Nếu danh mục có Parser đã đăng ký trong Registry -> gọi parser tương ứng.
        3. Đọc động tất cả Spec Definitions thuộc danh mục (hoặc toàn bộ spec definitions hoạt động).
        4. Khớp các mẫu thông số kỹ thuật chuẩn:
           - Răng / Teeth: '10 răng', '10r', '10R', 'rang: 10'
           - Lò xo / Springs: '8 lò xo', '8 lx', '8LX', 'lo xo: 8'
           - Kích thước ngoài / Phi / mm: 'phi 325', '325mm', 'đường kính 325', 'ø325'
           - Số lỗ: '10 lỗ', 'lo: 10'
           - Chiều cao / Bề dày: 'chiều cao 150', 'dày 20'
        5. Xác định các token số chưa được gán nhãn (Unresolved Numerics).
        6. Phân giải an toàn số chưa gán nhãn nếu có bối cảnh danh mục (category/context/các specs khác cùng câu):
           - Trong danh mục LC (lá côn) hoặc khi có thông số đặc trưng (răng / lò xo):
             Số từ 150 - 500 mm chưa gán nhãn sẽ được phân giải thành duong_kinh_ngoai (Đường kính ngoài).
        7. Trả về: (parsed_specs, unresolved_numerics, inferred_category).
        """
        parsed_specs = {}
        consumed_spans = []

        # 1. Thu thập tất cả các token số trong câu hỏi
        numeric_matches = list(re.finditer(r'\b\d+(?:[.,]\d+)?\b', query))

        # Bảo vệ các mã SKU kỹ thuật (ví dụ LC.002, TBUA.010, HOWO-371) khỏi bị bóc tách thành số trần
        for m_sku in re.finditer(r'\b[A-Za-z0-9]+[\.-][A-Za-z0-9\.-]+\b', query):
            consumed_spans.append(m_sku.span())

        # 2. Thử gọi parser chuyên dụng từ registry nếu category đã xác định
        if category and "qba.spec.parser.registry" in self.env:
            parser = self.env["qba.spec.parser.registry"].get_parser_for_category(category)
            if parser is not None:
                parse_fn = getattr(parser, "parse_product_name", None) or getattr(parser, "parse_lc_name", None)
                if parse_fn:
                    try:
                        p_res = parse_fn(query)
                        if p_res and isinstance(p_res, dict):
                            for k, v in p_res.items():
                                if isinstance(v, dict) and "value" in v:
                                    parsed_specs[k] = v
                                    for m in numeric_matches:
                                        try:
                                            if float(m.group(0).replace(',', '.')) == float(v["value"]):
                                                consumed_spans.append(m.span())
                                        except ValueError:
                                            pass
                    except Exception as e:
                        _logger.debug("Lỗi khi gọi parser chuyên dụng cho %s: %s", category.display_name, e)

        # 3. Quét động các qba.product.spec.definition trong database
        domain_specs = [('active', '=', True)]
        if category:
            domain_specs.append(('category_ids', 'in', [category.id]))

        spec_defs = self.env['qba.product.spec.definition'].search(domain_specs)
        for spec_def in spec_defs:
            code = spec_def.code
            if code in parsed_specs:
                continue

            name = spec_def.name.lower()
            uom = spec_def.uom or ""

            # Không cho phép các đơn vị đo lường dùng chung (mm, cái, kg...) tự ý bắt số nếu không kèm tên thông số cụ thể
            unit_postfix = (
                r'|' + re.escape(uom)
                if (uom and uom.lower() not in ('mm', 'cm', 'm', 'kg', 'cái', 'viên', 'bộ', 'con'))
                else ''
            )
            name_postfix = (r'|' + re.escape(name)) if len(name) > 2 else ''
            allowed_postfix = (unit_postfix + name_postfix).lstrip('|')

            if allowed_postfix:
                pat = (
                    r'(?:(?:' + re.escape(name) + r'|' + re.escape(code) + r')\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(?:' + re.escape(uom) + r')?'
                    r'|\b(\d+(?:[.,]\d+)?)\s*(?:' + allowed_postfix + r')\b)'
                )
            else:
                pat = r'(?:' + re.escape(name) + r'|' + re.escape(code) + r')\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(?:' + re.escape(uom) + r')?'
            match = re.search(pat, query, re.I)
            if match:
                raw_num = (match.group(1) or match.group(2)).replace(',', '.')
                val = float(raw_num) if spec_def.data_type == 'float' else int(float(raw_num))
                parsed_specs[code] = {
                    "value": val,
                    "uom": uom,
                    "spec_name": spec_def.name,
                }
                span_to_consume = match.span(1) if match.group(1) else match.span(2)
                consumed_spans.append(span_to_consume)

        # 4. Quét các mẫu kích thước / thông số dạng phổ biến (Generic Dimensional Patterns)
        # 4.1. Số răng (teeth): "10 răng", "10R", "10r", "răng 10", "rang: 10"
        if "rang" not in parsed_specs and "teeth" not in parsed_specs:
            m_teeth = re.search(r'(?:(?:răng|rang|teeth)\s*[:=]?\s*(\d+)|\b(\d+)\s*[rR]\b|\b(\d+)\s*răng\b|\b(\d+)\s*rang\b)', query, re.I)
            if m_teeth:
                teeth_val = m_teeth.group(1) or m_teeth.group(2) or m_teeth.group(3) or m_teeth.group(4)
                parsed_specs["rang"] = {"value": int(teeth_val), "uom": "răng", "spec_name": _("Số răng")}
                for g in (1, 2, 3, 4):
                    if m_teeth.group(g):
                        consumed_spans.append(m_teeth.span(g))

        # 4.2. Số lò xo (springs / lo xo): "8 lò xo", "8 lx", "8LX", "lò xo: 8"
        if "lo_xo" not in parsed_specs and "springs" not in parsed_specs:
            m_springs = re.search(r'(?:(?:số\s+lò\s+xo|lò\s+xo|lo\s+xo|springs?)\s*[:=]?\s*(\d+)|\b(\d+)\s*(?:lò\s+xo|lo\s+xo|lx|LX)\b)', query, re.I)
            if m_springs:
                spring_val = m_springs.group(1) or m_springs.group(2)
                parsed_specs["lo_xo"] = {
                    "value": int(spring_val),
                    "uom": "cái",
                    "spec_name": _("Số lò xo")
                }
                for g in (1, 2):
                    if m_springs.group(g):
                        consumed_spans.append(m_springs.span(g))

        # 4.3. Đường kính ngoài / Phi / Kích thước ngoài: "phi 325", "325mm", "đường kính 325"
        if "duong_kinh_ngoai" not in parsed_specs and "duong_kinh" not in parsed_specs:
            m_diam = re.search(r'(?:(?:đường\s+kính\s+ngoài|đk\s+ngoài|đường\s+kính|phi|ø|diam(?:eter)?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*mm)\b', query, re.I)
            if m_diam:
                raw_val = m_diam.group(1) or m_diam.group(2)
                parsed_specs["duong_kinh_ngoai"] = {
                    "value": float(raw_val.replace(",", ".")),
                    "uom": "mm",
                    "spec_name": _("Đường kính ngoài")
                }
                for g in (1, 2):
                    if m_diam.group(g):
                        consumed_spans.append(m_diam.span(g))

        # 4.4. Số lỗ / Số bulong: "10 lỗ"
        if "so_lo" not in parsed_specs and "so_lo_bulong" not in parsed_specs:
            m_holes = re.search(r'(?:số\s+lỗ|so\s+lo|lỗ\s+bulong|lỗ|holes?)\s*[:=]?\s*(\d+)', query, re.I)
            if m_holes:
                parsed_specs["so_lo"] = {"value": int(m_holes.group(1)), "uom": "lỗ", "spec_name": _("Số lỗ")}
                consumed_spans.append(m_holes.span(1))

        # 4.5. Chiều cao / Bề dày
        if "chieu_cao" not in parsed_specs and "do_day" not in parsed_specs:
            m_h = re.search(r'(?:chiều\s+cao|chieu\s+cao|độ\s+dày|do\s+day|height|thick(?:ness)?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)', query, re.I)
            if m_h:
                parsed_specs["chieu_cao"] = {
                    "value": float(m_h.group(1).replace(",", ".")),
                    "uom": "mm",
                    "spec_name": _("Chiều cao / Bề dày")
                }
                consumed_spans.append(m_h.span(1))

        # 5. Xác định các số chưa được gán nhãn (Unresolved Numerics)
        unresolved_numerics = []
        for m in numeric_matches:
            s_start, s_end = m.span()
            is_consumed = any(cs[0] <= s_start and s_end <= cs[1] for cs in consumed_spans)
            if not is_consumed:
                try:
                    num_val = float(m.group(0).replace(',', '.'))
                    unresolved_numerics.append(num_val)
                except ValueError:
                    pass

        # 6. Phân giải thông số từ Unresolved Numerics dựa trên ngữ cảnh hoặc các thông số khác trong cùng câu
        inferred_category = category
        if not inferred_category and parsed_specs:
            spec_codes = list(parsed_specs.keys())
            defs = self.env['qba.product.spec.definition'].search([('code', 'in', spec_codes)])
            cand_cats = defs.mapped('category_ids')
            if len(cand_cats) == 1:
                inferred_category = cand_cats[0]

        resolved_nums = []
        if inferred_category:
            cat_name = (inferred_category.name or "").lower()
            if "lc" in cat_name or "lá côn" in cat_name or "đĩa ly hợp" in cat_name:
                # Với Lá Côn: nếu chưa có đường kính ngoài, số trong khoảng 150..500 là đường kính ngoài
                if "duong_kinh_ngoai" not in parsed_specs and "duong_kinh" not in parsed_specs:
                    for num in unresolved_numerics:
                        if 150 <= num <= 500:
                            parsed_specs["duong_kinh_ngoai"] = {
                                "value": float(num),
                                "uom": "mm",
                                "spec_name": _("Đường kính ngoài")
                            }
                            resolved_nums.append(num)
                            break
                # Nếu chưa có răng, số nguyên 8..30 là số răng
                if "rang" not in parsed_specs and "teeth" not in parsed_specs:
                    for num in unresolved_numerics:
                        if num not in resolved_nums and num == int(num) and 8 <= num <= 30:
                            parsed_specs["rang"] = {
                                "value": int(num),
                                "uom": "răng",
                                "spec_name": _("Số răng")
                            }
                            resolved_nums.append(num)
                            break

        unresolved_numerics = [n for n in unresolved_numerics if n not in resolved_nums]
        if return_details:
            return parsed_specs, unresolved_numerics, inferred_category
        return parsed_specs

    @api.model
    def _resolve_product_by_code_or_name(self, text):
        """Tìm sản phẩm cơ sở bằng mã hoặc tên trích xuất từ câu hỏi"""
        clean_text = text.strip()
        # Thử tìm chính xác bằng default_code
        prod = self.env['product.template'].search([('default_code', '=ilike', clean_text)], limit=1)
        if prod:
            return (prod, prod.default_code)

        # Trích xuất token SKU trong chuỗi
        tokens = re.findall(r'\b[A-Za-z0-9]+[A-Za-z0-9\.-]{2,}\b', clean_text)
        for t in tokens:
            prod = self.env['product.template'].search([('default_code', '=ilike', t)], limit=1)
            if prod:
                return (prod, t)

        # Tìm bằng name ilike
        prod_name = self.env['product.template'].search([('name', 'ilike', clean_text)], limit=1)
        if prod_name:
            return (prod_name, prod_name.default_code or clean_text)

        return (False, clean_text)

    @api.model
    def _is_ambiguous_query(self, query):
        """Xác định xem truy vấn có quá mơ hồ hoặc không đủ căn cứ xử lý an toàn không"""
        q = query.strip()
        if len(q) < 3:
            return True

        # Nếu chỉ gồm toàn ký tự đặc biệt
        if not re.search(r'[A-Za-z0-9]', q):
            return True

        # Nếu chỉ gồm các từ giao tiếp / từ dừng thông thường
        tokens = [t.lower() for t in re.sub(r'[^\w\s]', ' ', q).split() if len(t) >= 2]
        if not tokens:
            return True

        content_tokens = [t for t in tokens if t not in self.STOP_WORDS]
        if not content_tokens:
            return True

        return False

    @api.model
    def _extract_clean_tokens(self, query):
        """Trích xuất danh sách từ khóa có ý nghĩa nghiệp vụ (đã lọc stop words)"""
        raw_clean = re.sub(r'[^\w\s\.-]', ' ', query).strip()
        tokens = [t for t in raw_clean.split() if len(t) >= 2 and t.lower() not in self.STOP_WORDS]
        return tokens or [t for t in raw_clean.split() if len(t) >= 2]

    @api.model
    def _build_router_result(self, intent, label, query, target_sku=None, target_product=None,
                             target_category=None, extracted_specs=None, equipment_terms=None,
                             clean_terms=None, clean_query=None, is_ambiguous=False, clarification=None,
                             unresolved_numerics=None, confidence="high", product_category_terms=None):
        """Đóng gói kết quả điều hướng intent chuẩn hóa"""
        badge_classes = {
            "exact_sku": "bg-primary text-white",
            "explicit_replacement": "bg-success text-white",
            "technical_spec_only": "bg-info text-dark",
            "equipment_context": "bg-warning text-dark",
            "product_name_alias": "bg-secondary text-white",
            "natural_language_description": "bg-dark text-white",
            "ambiguous": "bg-danger text-white",
        }
        badge_class = badge_classes.get(intent, "bg-secondary text-white")
        badge_html = f"<span class='badge {badge_class}'><i class='fa fa-compass me-1'></i>{html_escape(label)}</span>"

        cat_terms = product_category_terms or []
        if not cat_terms and target_category:
            cat_terms = [target_category.name]

        return {
            "intent": intent,
            "intent_label": label,
            "intent_badge_html": badge_html,
            "raw_query": query,
            "target_sku": target_sku,
            "target_product": target_product,
            "target_category": target_category,
            "product_category_terms": cat_terms,
            "extracted_specs": extracted_specs or {},
            "unresolved_numerics": unresolved_numerics or [],
            "confidence": confidence,
            "equipment_terms": equipment_terms or [],
            "clean_terms": clean_terms or [],
            "clean_query": clean_query or query,
            "is_ambiguous": is_ambiguous,
            "clarification_message": clarification,
        }
