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
    def route_query(self, query):
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
        detected_category = self._detect_category(raw_query)
        extracted_specs = self._extract_technical_specs(raw_query, category=detected_category)
        if extracted_specs:
            return self._build_router_result(
                intent="technical_spec_only",
                label=_("Tra cứu theo thông số kỹ thuật"),
                query=raw_query,
                target_category=detected_category,
                extracted_specs=extracted_specs,
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
        # Loại bỏ các tiền tố như "mã:", "sku:", "code:"
        clean_q = re.sub(r'^(?:mã|sku|code|part\s*no\.?)\s*[:=]?\s*', '', clean_q, flags=re.I).strip()

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

        return (False, False)

    @api.model
    def _detect_replacement_intent(self, query):
        """Phát hiện ý định tìm phụ tùng thay thế (Explicit Replacement Search)"""
        for pat in self.REPLACEMENT_KEYWORDS:
            match = re.search(pat, query, re.I)
            if match:
                remainder = query[match.end():].strip()
                remainder = re.sub(r'^(?:cho\s+)?(?:mã\s+|sản\s+phẩm\s+|sp\s+)?', '', remainder, flags=re.I).strip()
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
        best_score = -1

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
    def _extract_technical_specs(self, query, category=None):
        """Trích xuất thông số kỹ thuật đa danh mục dựa trên định nghĩa CSDL (Data-Driven).
        1. Nếu danh mục có Parser đã đăng ký trong Registry -> gọi parser tương ứng.
        2. Đọc động tất cả Spec Definitions thuộc danh mục (hoặc toàn bộ spec definitions hoạt động).
        3. Khớp các mẫu thông số: <tên/mã thông số>[:=]? <giá trị> <đơn vị>.
        4. Khớp các thông số kích thước phổ biến (phi/đường kính/mm, số răng, số lỗ...).
        """
        parsed_specs = {}

        # 1. Thử gọi parser chuyên dụng từ registry nếu category đã xác định
        if category and "qba.spec.parser.registry" in self.env:
            parser = self.env["qba.spec.parser.registry"].get_parser_for_category(category)
            if parser:
                parse_fn = getattr(parser, "parse_product_name", None) or getattr(parser, "parse_lc_name", None)
                if parse_fn:
                    try:
                        p_res = parse_fn(query)
                        if p_res and isinstance(p_res, dict):
                            for k, v in p_res.items():
                                if isinstance(v, dict) and "value" in v:
                                    parsed_specs[k] = v
                    except Exception as e:
                        _logger.debug("Lỗi khi gọi parser chuyên dụng cho %s: %s", category.display_name, e)

        # 2. Quét động các qba.product.spec.definition trong database
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

            # Xây dựng regex tìm tên thông số hoặc mã thông số kèm giá trị số
            # Ví dụ: "răng: 10", "đường kính 325", "d: 50"
            pat = r'(?:' + re.escape(name) + r'|' + re.escape(code) + r')\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(?:' + re.escape(uom) + r')?'
            match = re.search(pat, query, re.I)
            if match:
                raw_num = match.group(1).replace(',', '.')
                val = float(raw_num) if spec_def.data_type == 'float' else int(float(raw_num))
                parsed_specs[code] = {
                    "value": val,
                    "uom": uom,
                    "spec_name": spec_def.name,
                }

        # 3. Quét các mẫu kích thước / thông số dạng phổ biến (Generic Dimensional Patterns)
        # 3.1. Số răng (teeth)
        if "rang" not in parsed_specs and "teeth" not in parsed_specs:
            m_teeth = re.search(r'(?:(?:răng|rang|teeth)\s*[:=]?\s*(\d+)|\b(\d+)\s*[rR]\b|\b(\d+)\s*răng\b)', query, re.I)
            if m_teeth:
                teeth_val = m_teeth.group(1) or m_teeth.group(2) or m_teeth.group(3)
                parsed_specs["rang"] = {"value": int(teeth_val), "uom": "răng", "spec_name": _("Số răng")}

        # 3.2. Đường kính ngoài / Phi / Kích thước ngoài
        if "duong_kinh_ngoai" not in parsed_specs and "duong_kinh" not in parsed_specs:
            m_diam = re.search(r'(?:(?:đường\s+kính\s+ngoài|đk\s+ngoài|đường\s+kính|phi|ø|diam(?:eter)?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*mm)\b', query, re.I)
            if m_diam:
                raw_val = m_diam.group(1) or m_diam.group(2)
                parsed_specs["duong_kinh_ngoai"] = {
                    "value": float(raw_val.replace(",", ".")),
                    "uom": "mm",
                    "spec_name": _("Đường kính ngoài")
                }

        # 3.3. Số lỗ / Số bulong (phổ biến cho tăm bua, mâm, bánh đà)
        if "so_lo" not in parsed_specs and "so_lo_bulong" not in parsed_specs:
            m_holes = re.search(r'(?:số\s+lỗ|so\s+lo|lỗ\s+bulong|lỗ|holes?)\s*[:=]?\s*(\d+)', query, re.I)
            if m_holes:
                parsed_specs["so_lo"] = {"value": int(m_holes.group(1)), "uom": "lỗ", "spec_name": _("Số lỗ")}

        # 3.4. Chiều cao / Bề dày
        if "chieu_cao" not in parsed_specs and "do_day" not in parsed_specs:
            m_h = re.search(r'(?:chiều\s+cao|chieu\s+cao|độ\s+dày|do\s+day|height|thick(?:ness)?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)', query, re.I)
            if m_h:
                parsed_specs["chieu_cao"] = {
                    "value": float(m_h.group(1).replace(",", ".")),
                    "uom": "mm",
                    "spec_name": _("Chiều cao / Bề dày")
                }

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
                             clean_terms=None, clean_query=None, is_ambiguous=False, clarification=None):
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

        return {
            "intent": intent,
            "intent_label": label,
            "intent_badge_html": badge_html,
            "raw_query": query,
            "target_sku": target_sku,
            "target_product": target_product,
            "target_category": target_category,
            "extracted_specs": extracted_specs or {},
            "equipment_terms": equipment_terms or [],
            "clean_terms": clean_terms or [],
            "clean_query": clean_query or query,
            "is_ambiguous": is_ambiguous,
            "clarification_message": clarification,
        }
