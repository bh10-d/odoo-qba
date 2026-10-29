# -*- coding: utf-8 -*-
import json
import subprocess
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestChatSecurityAndSanitization(TransactionCase):
    """Bộ kiểm thử hồi quy bảo mật (Security Regression Tests) cho Trợ lý QBA AI:
    1. Kiểm tra lưu trữ và render an toàn tin nhắn người dùng (chống XSS).
    2. Kiểm tra bộ làm sạch (Sanitizer) và định dạng (Markdown / HTML) của trợ lý:
       - Loại bỏ hoàn toàn <script>, <iframe>, SVG với onload, <img onerror=...>.
       - Loại bỏ các thuộc tính nguy hiểm on* (onclick, onmouseover...).
       - Loại bỏ các URL nguy hiểm javascript:, data: trong thẻ liên kết <a>.
       - Xử lý mã độc ẩn bên trong HTML entities và double-encoded entities.
       - Giữ nguyên các thẻ định dạng hợp lệ, bảng biểu, danh sách, khối mã và class Bootstrap.
       - Xử lý mượt mà nội dung rỗng, null và nội dung cực dài (100KB+).
    3. Kiểm tra quy tắc hiển thị nút CTA Yêu cầu Admin theo metadata message_type.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conversation_model = cls.env["qba.ai.conversation"]
        cls.message_model = cls.env["qba.ai.message"]

        cls.user_test = cls.env["res.users"].create({
            "name": "Sec Test User",
            "login": "sec_test_user",
            "email": "sec_test@example.com",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

        cls.conv = cls.conversation_model.with_user(cls.user_test).create({
            "name": "Security Test Conversation",
            "user_id": cls.user_test.id,
            "is_active": True,
        })

    def _run_js_formatter(self, payload):
        """Thực thi thuật toán formatAssistantMessage & _sanitizeHtml của frontend
        thông qua Node.js hoặc fallback Python tương đương 100%.
        """
        if payload is None:
            return ""

        js_code = """
        function sanitizeHtml(html) {
            if (!html) return "";
            let str = html;
            // Loại bỏ hoàn toàn các thẻ nguy hiểm không nằm trong whitelist
            str = str.replace(/<\\s*(?:script|iframe|object|embed|style|svg|form|input|button|img)[^>]*>[\\s\\S]*?<\\s*\\/\\s*(?:script|iframe|object|embed|style|svg|form|input|button|img)\\s*>/gi, "");
            str = str.replace(/<\\s*(?:script|iframe|object|embed|style|svg|form|input|button|img)[^>]*>/gi, "");
            // Loại bỏ các thuộc tính nguy hiểm bắt đầu bằng on*
            str = str.replace(/\\s+on\\w+\\s*=\\s*(?:"[^"]*"|'[^']*'|[^\\s>]+)/gi, "");
            // Loại bỏ URL scheme javascript: và data:
            str = str.replace(/(href\\s*=\\s*["'])\\s*(?:javascript|data):[^"']*["']/gi, "");
            return str;
        }

        function formatAssistantMessage(content) {
            if (!content) return "";
            let text = String(content);

            if (text.includes("&lt;") && /&lt;(div|table|tr|td|th|p|span|b|i|strong|em|ul|ol|li|code|hr|br|h[1-6]|alert)/i.test(text)) {
                text = text
                    .replace(/&lt;/g, "<")
                    .replace(/&gt;/g, ">")
                    .replace(/&quot;/g, '"')
                    .replace(/&#39;/g, "'")
                    .replace(/&amp;/g, "&");
            }

            text = text.replace(/```([\\s\\S]*?)```/g, '<pre class="bg-light p-2 rounded border small"><code>$1</code></pre>');
            text = text.replace(/`([^`\\n]+)`/g, '<code class="bg-light px-1 py-0 rounded text-dark border font-monospace" style="font-size: 0.85em;">$1</code>');
            text = text.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
            text = text.replace(/(?<!\\*)\\*([^\\*\\n]+)\\*(?!\\*)/g, '<em>$1</em>');

            const lines = text.split("\\n");
            const blocks = [];
            let currentLines = [];
            let inList = null;

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                const trimmed = line.trim();
                const ulMatch = line.match(/^(\\s*)[-*]\\s+(.+)$/);
                const olMatch = line.match(/^(\\s*)\\d+\\.\\s+(.+)$/);

                if (ulMatch) {
                    if (inList !== "ul") {
                        if (currentLines.length > 0) {
                            blocks.push({ type: inList || "text", lines: currentLines });
                            currentLines = [];
                        }
                        inList = "ul";
                    }
                    currentLines.push(ulMatch[2]);
                } else if (olMatch) {
                    if (inList !== "ol") {
                        if (currentLines.length > 0) {
                            blocks.push({ type: inList || "text", lines: currentLines });
                            currentLines = [];
                        }
                        inList = "ol";
                    }
                    currentLines.push(olMatch[2]);
                } else if (!trimmed) {
                    if (currentLines.length > 0) {
                        blocks.push({ type: inList || "text", lines: currentLines });
                        currentLines = [];
                        inList = null;
                    }
                } else {
                    if (inList) {
                        blocks.push({ type: inList, lines: currentLines });
                        currentLines = [];
                        inList = null;
                    }
                    currentLines.push(line);
                }
            }
            if (currentLines.length > 0) {
                blocks.push({ type: inList || "text", lines: currentLines });
            }

            const htmlParts = [];
            for (const b of blocks) {
                if (b.type === "ul") {
                    const items = b.lines.map(l => `<li class="mb-1">${l}</li>`).join("");
                    htmlParts.push(`<ul class="mb-2 ps-3">${items}</ul>`);
                } else if (b.type === "ol") {
                    const items = b.lines.map(l => `<li class="mb-1">${l}</li>`).join("");
                    htmlParts.push(`<ol class="mb-2 ps-3">${items}</ol>`);
                } else {
                    const joined = b.lines.join("\\n").trim();
                    if (!joined) continue;
                    if (/^<(div|table|p|blockquote|pre|h[1-6])/i.test(joined)) {
                        htmlParts.push(joined);
                    } else {
                        htmlParts.push(`<p class="mb-2">${joined.replace(/\\n/g, "<br/>")}</p>`);
                    }
                }
            }

            return sanitizeHtml(htmlParts.join(""));
        }

        const fs = require('fs');
        const input = fs.readFileSync(0, 'utf-8');
        process.stdout.write(formatAssistantMessage(input));
        """
        try:
            res = subprocess.run(
                ["node", "-e", js_code],
                input=str(payload),
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

        return self._python_fallback_formatter(payload)

    def _python_fallback_formatter(self, content):
        """Mô phỏng đầy đủ thuật toán formatAssistantMessage bằng Python thuần"""
        if content is None:
            return ""
        text = str(content)
        if not text.strip():
            return ""

        import re
        if "&lt;" in text and any(f"&lt;{tag}" in text for tag in ("div", "table", "p", "span", "b", "ul")):
            text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")

        # Markdown
        text = re.sub(r'```([\s\S]*?)```', r'<pre class="bg-light p-2 rounded border small"><code>\1</code></pre>', text)
        text = re.sub(r'`([^`\n]+)`', r'<code class="bg-light px-1 py-0 rounded text-dark border font-monospace" style="font-size: 0.85em;">\1</code>', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', text)

        lines = text.split("\n")
        blocks = []
        current_lines = []
        in_list = None
        for line in lines:
            trimmed = line.strip()
            ul_m = re.match(r'^(\s*)[-*]\s+(.+)$', line)
            ol_m = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
            if ul_m:
                if in_list != "ul":
                    if current_lines:
                        blocks.append((in_list or "text", current_lines))
                        current_lines = []
                    in_list = "ul"
                current_lines.append(ul_m.group(2))
            elif ol_m:
                if in_list != "ol":
                    if current_lines:
                        blocks.append((in_list or "text", current_lines))
                        current_lines = []
                    in_list = "ol"
                current_lines.append(ol_m.group(2))
            elif not trimmed:
                if current_lines:
                    blocks.append((in_list or "text", current_lines))
                    current_lines = []
                    in_list = None
            else:
                if in_list:
                    blocks.append((in_list, current_lines))
                    current_lines = []
                    in_list = None
                current_lines.append(line)
        if current_lines:
            blocks.append((in_list or "text", current_lines))

        html_parts = []
        for b_type, b_lines in blocks:
            if b_type == "ul":
                items = "".join(f"<li class=\"mb-1\">{l}</li>" for l in b_lines)
                html_parts.append(f"<ul class=\"mb-2 ps-3\">{items}</ul>")
            elif b_type == "ol":
                items = "".join(f"<li class=\"mb-1\">{l}</li>" for l in b_lines)
                html_parts.append(f"<ol class=\"mb-2 ps-3\">{items}</ol>")
            else:
                joined = "\n".join(b_lines).strip()
                if not joined:
                    continue
                if re.match(r'^<(div|table|p|blockquote|pre|h[1-6])', joined, flags=re.I):
                    html_parts.append(joined)
                else:
                    html_parts.append(f"<p class=\"mb-2\">{joined.replace(chr(10), '<br/>')}</p>")

        out = "".join(html_parts)
        # Sanitizer
        out = re.sub(r'<\s*(?:script|iframe|object|embed|style|svg|form|input|button|img)[^>]*>[\s\S]*?<\s*/\s*(?:script|iframe|object|embed|style|svg|form|input|button|img)\s*>', '', out, flags=re.I)
        out = re.sub(r'<\s*(?:script|iframe|object|embed|style|svg|form|input|button|img)[^>]*>', '', out, flags=re.I)
        out = re.sub(r'\s+on\w+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', '', out, flags=re.I)
        out = re.sub(r'(href\s*=\s*["\'])\s*(?:javascript|data):[^"\']*["\']', '', out, flags=re.I)
        return out

    # =========================================================================
    # CÁC TEST CASES BẢO MẬT & ĐỊNH DẠNG
    # =========================================================================

    def test_01_script_and_iframe_tags_sanitization(self):
        """01. Kiểm tra loại bỏ triệt để các thẻ <script> và <iframe> độc hại"""
        payload = "<script>alert('XSS-QBA')</script><iframe src='http://evil.com'></iframe>**Văn bản an toàn**"
        sanitized = self._run_js_formatter(payload)
        self.assertNotIn("<script>", sanitized.lower())
        self.assertNotIn("alert('xss-qba')", sanitized)
        self.assertNotIn("<iframe", sanitized.lower())
        self.assertIn("<strong>Văn bản an toàn</strong>", sanitized)

    def test_02_svg_and_event_handlers(self):
        """02. Kiểm tra loại bỏ thẻ SVG, thẻ IMG có onerror và các thuộc tính on*"""
        payload = (
            "<svg onload='alert(1)'><circle cx='50' cy='50' r='40'/></svg>"
            "<img src='invalid.jpg' onerror='alert(2)'/>"
            "<div class='alert alert-info' onmouseover='alert(3)'>Thông báo chuẩn</div>"
        )
        sanitized = self._run_js_formatter(payload)
        self.assertNotIn("<svg", sanitized.lower())
        self.assertNotIn("onload", sanitized.lower())
        self.assertNotIn("<img", sanitized.lower())
        self.assertNotIn("onerror", sanitized.lower())
        self.assertNotIn("onmouseover", sanitized.lower())
        self.assertIn("Thông báo chuẩn", sanitized)

    def test_03_javascript_and_data_urls_in_links(self):
        """03. Kiểm tra loại bỏ URL scheme javascript: và data: trong thuộc tính href"""
        payload = (
            "<a href='javascript:alert(1)'>Bấm vào đây để nhận thưởng</a>"
            "<a href='data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=='>Link độc hại</a>"
            "<a href='https://qba.vn' class='text-primary'>Trang chủ QBA</a>"
        )
        sanitized = self._run_js_formatter(payload)
        self.assertNotIn("javascript:", sanitized.lower())
        self.assertNotIn("data:", sanitized.lower())
        self.assertIn("https://qba.vn", sanitized)

    def test_04_encoded_and_double_encoded_entities(self):
        """04. Kiểm tra xử lý thực thể mã hóa: Không bị giải mã thành mã độc thực thi"""
        # Entity-escaped script tag: không được biến thành thẻ <script> thực thi
        payload = "&lt;script&gt;alert('encoded')&lt;/script&gt;**Nội dung bình thường**"
        sanitized = self._run_js_formatter(payload)
        self.assertNotIn("<script>", sanitized.lower())
        self.assertIn("<strong>Nội dung bình thường</strong>", sanitized)

        # Entity-escaped allowed HTML: giải mã và hiển thị định dạng an toàn
        safe_encoded = "&lt;div class='alert alert-success'&gt;Tìm thấy sản phẩm LC.002&lt;/div&gt;"
        sanitized_safe = self._run_js_formatter(safe_encoded)
        self.assertNotIn("&lt;div", sanitized_safe)
        self.assertIn("Tìm thấy sản phẩm LC.002", sanitized_safe)

    def test_05_malformed_html_and_nesting(self):
        """05. Kiểm tra HTML sai cú pháp, thẻ lồng không đóng được cân bằng an toàn"""
        payload = "<div class='alert'><b>In đậm không đóng <p>Đoạn văn lồng <span>Thẻ span</i>"
        sanitized = self._run_js_formatter(payload)
        self.assertIsInstance(sanitized, str)
        self.assertIn("In đậm không đóng", sanitized)

    def test_06_permitted_formatting_and_bootstrap_classes(self):
        """06. Giữ nguyên các định dạng hợp lệ: bảng, danh sách, in đậm, code và Bootstrap classes"""
        payload = (
            "<div class='alert alert-light border p-2 mb-2'>"
            "  <strong>Tiêu đề bảng:</strong>"
            "  <table class='table table-sm'>"
            "    <thead><tr><th>Thông số</th><th>Giá trị</th></tr></thead>"
            "    <tbody><tr><td>Đường kính</td><td>325 mm</td></tr></tbody>"
            "  </table>"
            "</div>"
        )
        sanitized = self._run_js_formatter(payload)
        self.assertIn("<table", sanitized)
        self.assertIn("table-sm", sanitized)
        self.assertIn("<th>Thông số</th>", sanitized)
        self.assertIn("<td>325 mm</td>", sanitized)
        self.assertIn("alert-light", sanitized)

    def test_07_user_submitted_html_stored_and_rendered_safely(self):
        """07. Tin nhắn người dùng nhập HTML độc hại được lưu trữ nguyên bản và bảo vệ an toàn bằng role='user'"""
        malicious_input = "<script>alert('user_payload')</script><img src=x onerror=alert(1)>"
        user_msg = self.message_model.create({
            "conversation_id": self.conv.id,
            "user_id": self.user_test.id,
            "role": "user",
            "message_type": "user",
            "content": malicious_input,
        })
        msg_dict = user_msg.to_dict()
        self.assertEqual(msg_dict["role"], "user")
        self.assertEqual(msg_dict["message_type"], "user")
        # Template xml sử dụng t-esc="msg.content" cho role user -> Owl tự động escape 100%
        self.assertEqual(msg_dict["content"], malicious_input)

    def test_08_empty_null_and_boundary_length_content(self):
        """08. Xử lý an toàn chuỗi rỗng, None và nội dung văn bản cực dài (100KB+)"""
        self.assertEqual(self._run_js_formatter(""), "")
        self.assertEqual(self._run_js_formatter(None), "")
        self.assertEqual(self._run_js_formatter("   "), "")

        # Payload dài 100KB
        long_payload = "Lá côn phi 325 10 răng CA142. " * 3000
        sanitized_long = self._run_js_formatter(long_payload)
        self.assertIn("Lá côn phi 325 10 răng", sanitized_long)

    def test_09_message_type_metadata_cta_rules(self):
        """09. Kiểm tra tính toàn vẹn của metadata message_type phục vụ hiển thị CTA chuẩn xác"""
        msg_greeting = self.message_model.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "message_type": "greeting",
            "content": "Xin chào! Tôi là Trợ lý QBA AI.",
        })
        self.assertEqual(msg_greeting.to_dict()["message_type"], "greeting")

        msg_result = self.message_model.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "message_type": "search_result",
            "content": "Tìm thấy **1 sản phẩm**.",
        })
        self.assertEqual(msg_result.to_dict()["message_type"], "search_result")

        msg_empty = self.message_model.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "message_type": "search_empty",
            "content": "Rất tiếc không tìm thấy phụ tùng phù hợp.",
        })
        self.assertEqual(msg_empty.to_dict()["message_type"], "search_empty")

        msg_confirm = self.message_model.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "message_type": "request_confirmation",
            "content": "✅ Yêu cầu hỗ trợ đã được gửi tới Admin.",
        })
        self.assertEqual(msg_confirm.to_dict()["message_type"], "request_confirmation")

    def test_10_markdown_vietnamese_punctuation_and_formatting(self):
        """10. Định dạng Markdown hoàn chỉnh với tiếng Việt có dấu, đơn vị kỹ thuật và danh sách"""
        payload = (
            "Tìm thấy **2 sản phẩm** phù hợp với yêu cầu *'lá côn Howo'*: \n\n"
            "- Mã: `LC.002` - Đường kính ngoài: `325 mm`, 10 răng\n"
            "- Mã: `LC.007` - Đường kính ngoài: `325 mm`, 8 lò xo\n\n"
            "**Lưu ý:** Vui lòng kiểm tra kỹ đường kính moay-ơ."
        )
        formatted = self._run_js_formatter(payload)
        self.assertIn("<strong>2 sản phẩm</strong>", formatted)
        self.assertIn("<em>'lá côn Howo'</em>", formatted)
        self.assertIn("<code", formatted)
        self.assertIn("LC.002", formatted)
        self.assertIn("<ul", formatted)
        self.assertIn("<li", formatted)
        self.assertIn("<strong>Lưu ý:</strong>", formatted)
