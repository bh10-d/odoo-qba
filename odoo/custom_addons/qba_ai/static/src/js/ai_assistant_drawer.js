/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef, useEffect, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class QbaAiAssistantDrawer extends Component {
    static template = "qba_ai.QbaAiAssistantDrawer";
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.messagesEndRef = useRef("messagesEnd");
        this.inputRef = useRef("composerInput");
        this.currentRequestId = 0; // Concurrency token: Ngăn chặn race-condition khi click liên tiếp

        this.state = useState({
            isOpen: false,
            isLoading: false,
            isSending: false,
            showHistory: false,
            historyList: [],
            isLoadingHistory: false,
            conversationId: null,
            conversationName: "Hội thoại mới",
            conversationState: "active",
            contextProduct: null, // { id, name, default_code, category_name }
            searchContext: {},
            messages: [],
            inputValue: "",
            errorMessage: "",
            showRequestModal: false,
            isSubmittingRequest: false,
            requestFormError: "",
            requestForm: {
                type: "missing_product",
                query: "",
                productId: null,
                productName: "",
                productCode: "",
                specsSummary: "",
                notes: "",
                messageId: null,
            },
        });

        // Đăng ký lắng nghe sự kiện bus mở drawer từ các view Odoo hoặc window
        const onOpenDrawerEvent = (ev) => {
            const params = ev.detail || {};
            this.openDrawer(params);
        };
        this.env.bus.addEventListener("QBA_AI_OPEN_DRAWER", onOpenDrawerEvent);
        window.addEventListener("QBA_AI_OPEN_DRAWER", onOpenDrawerEvent);

        // Tự động cuộn xuống tin nhắn mới nhất khi danh sách tin nhắn thay đổi
        useEffect(
            () => {
                if (this.state.isOpen && this.messagesEndRef.el) {
                    this.messagesEndRef.el.scrollIntoView({ behavior: "smooth" });
                }
            },
            () => [this.state.messages.length, this.state.isLoading, this.state.isOpen]
        );
    }

    /**
     * Mở Drawer trợ lý AI, nạp ngữ cảnh sản phẩm nếu có
     */
    async openDrawer(params = {}) {
        this.state.isOpen = true;
        this.state.showHistory = false;
        this.state.errorMessage = "";
        const contextProductId = params.product_id || null;
        const conversationId = params.conversation_id || null;

        // Nếu có chỉ định conversationId, hoặc contextProductId, hoặc drawer chưa nạp conversation nào:
        if (conversationId || contextProductId || !this.state.conversationId) {
            await this.loadActiveConversation(contextProductId, conversationId);
        }

        // Focus vào ô nhập liệu
        setTimeout(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
            }
        }, 150);
    }

    /**
     * Đóng Drawer
     */
    closeDrawer() {
        this.state.isOpen = false;
    }

    /**
     * Mở giao diện AI Assistant đầy đủ (Tra cứu kỹ thuật & Gửi Admin duyệt)
     */
    openAssistantView() {
        this.closeDrawer();
        this.actionService.doAction("qba_ai.action_qba_ai_assistant");
    }

    /**
     * Chuyển đổi trạng thái đóng/mở
     */
    toggleDrawer() {
        if (this.state.isOpen) {
            this.closeDrawer();
        } else {
            this.openDrawer();
        }
    }

    /**
     * Tải phiên hội thoại hiện tại hoặc theo ID từ server kèm cơ chế chống race-condition
     */
    async loadActiveConversation(contextProductId = null, conversationId = null) {
        const requestId = ++this.currentRequestId;
        this.state.isLoading = true;
        this.state.errorMessage = "";

        try {
            const res = await rpc("/qba_ai/conversation/get_active", {
                context_product_id: contextProductId,
                conversation_id: conversationId,
            });

            // Concurrency control: Bỏ qua phản hồi nếu người dùng đã bấm chuyển sang hội thoại mới hơn
            if (requestId !== this.currentRequestId) {
                return;
            }

            if (res.success && res.data) {
                this._applyConversationData(res.data);
            } else {
                this.state.errorMessage = res.error || "Không thể tải phiên hội thoại.";
                this.notificationService.add(this.state.errorMessage, { type: "danger" });
            }
        } catch (e) {
            if (requestId !== this.currentRequestId) {
                return;
            }
            this.state.errorMessage = "Lỗi kết nối máy chủ khi tải hội thoại: " + (e.message || e);
            this.notificationService.add(this.state.errorMessage, { type: "danger" });
        } finally {
            if (requestId === this.currentRequestId) {
                this.state.isLoading = false;
            }
        }
    }

    /**
     * Bật/tắt màn hình hiển thị danh sách các cuộc hội thoại cũ
     */
    async toggleHistory() {
        this.state.showHistory = !this.state.showHistory;
        if (this.state.showHistory) {
            await this.loadHistory();
        }
    }

    /**
     * Tải danh sách lịch sử các cuộc hội thoại từ backend
     */
    async loadHistory() {
        this.state.isLoadingHistory = true;
        try {
            const res = await rpc("/qba_ai/conversation/get_history", { limit: 30 });
            if (res.success && res.data) {
                this.state.historyList = res.data;
            } else {
                this.state.errorMessage = res.error || "Không thể nạp danh sách lịch sử.";
            }
        } catch (e) {
            this.state.errorMessage = "Lỗi tải lịch sử: " + (e.message || e);
        } finally {
            this.state.isLoadingHistory = false;
        }
    }

    /**
     * Chọn một cuộc hội thoại từ danh sách lịch sử để tiếp tục trò chuyện (dùng chung canonical loader)
     */
    async onSelectConversation(conversationId) {
        if (!conversationId) return;
        this.state.showHistory = false;
        await this.loadActiveConversation(null, conversationId);
    }

    /**
     * Khôi phục cuộc hội thoại từ trạng thái lưu trữ về đang hoạt động
     */
    async onRestoreConversation() {
        if (!this.state.conversationId) return;
        this.state.isLoading = true;
        try {
            const res = await rpc("/qba_ai/conversation/restore", {
                conversation_id: this.state.conversationId,
            });
            if (res.success && res.data) {
                this._applyConversationData(res.data);
                this.notificationService.add("Đã khôi phục hội thoại thành công.", { type: "info" });
            } else {
                this.state.errorMessage = res.error || "Không thể khôi phục hội thoại.";
                this.notificationService.add(this.state.errorMessage, { type: "danger" });
            }
        } catch (e) {
            this.state.errorMessage = "Lỗi khôi phục hội thoại: " + (e.message || e);
            this.notificationService.add(this.state.errorMessage, { type: "danger" });
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Xóa một cuộc hội thoại (trong danh sách lịch sử hoặc hội thoại hiện tại)
     */
    async onDeleteConversation(conversationId) {
        if (!conversationId) return;
        const confirmed = window.confirm("Bạn có chắc chắn muốn xóa vĩnh viễn cuộc hội thoại này?");
        if (!confirmed) return;

        this.state.isLoading = true;
        try {
            const res = await rpc("/qba_ai/conversation/delete", {
                conversation_id: conversationId,
            });
            if (res.success) {
                this.notificationService.add("Đã xóa cuộc hội thoại thành công.", { type: "info" });
                // Nếu xóa đúng hội thoại đang mở, khởi tạo phiên hội thoại mới sạch sẽ
                if (conversationId === this.state.conversationId) {
                    await this.onNewConversation();
                }
                // Nếu đang mở panel lịch sử, làm mới lại danh sách
                if (this.state.showHistory) {
                    await this.loadHistory();
                }
            } else {
                this.state.errorMessage = res.error || "Không thể xóa cuộc hội thoại.";
            }
        } catch (e) {
            this.state.errorMessage = "Lỗi khi xóa hội thoại: " + (e.message || e);
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Tạo một phiên hội thoại mới sạch sẽ
     */
    async onNewConversation() {
        if (this.state.isSending) return;
        this.state.isLoading = true;
        this.state.showHistory = false;
        try {
            const prodId = this.state.contextProduct ? this.state.contextProduct.id : null;
            const res = await rpc("/qba_ai/conversation/new", {
                context_product_id: prodId,
            });
            if (res.success && res.data) {
                this._applyConversationData(res.data);
                this.notificationService.add("Đã khởi tạo phiên hội thoại mới.", { type: "info" });
            } else {
                this.state.errorMessage = res.error || "Không thể tạo hội thoại mới.";
            }
        } catch (e) {
            this.state.errorMessage = "Lỗi tạo hội thoại mới: " + (e.message || e);
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Xóa sản phẩm ngữ cảnh để chuyển sang tìm kiếm danh mục chung
     */
    async onClearContextProduct() {
        if (!this.state.conversationId) return;
        this.state.isLoading = true;
        try {
            const res = await rpc("/qba_ai/conversation/clear_product", {
                conversation_id: this.state.conversationId,
            });
            if (res.success && res.data) {
                this._applyConversationData(res.data);
                this.notificationService.add("Đã gỡ sản phẩm ngữ cảnh. Trở về tìm kiếm toàn catalog.", { type: "info" });
            }
        } catch (e) {
            this.state.errorMessage = "Lỗi gỡ sản phẩm ngữ cảnh: " + (e.message || e);
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Gửi tin nhắn từ người dùng
     */
    async onSendMessage() {
        const text = (this.state.inputValue || "").trim();
        if (!text || this.state.isSending) return;

        // Xóa ô nhập liệu ngay lập tức
        this.state.inputValue = "";
        this.state.isSending = true;
        this.state.errorMessage = "";

        // Thêm tin nhắn tạm của user vào giao diện
        this.state.messages.push({
            id: "temp_" + Date.now(),
            role: "user",
            message_type: "user",
            content: text,
            create_date: new Date().toLocaleTimeString(),
            matched_products: [],
            explanation_html: "",
            perf_info: {},
        });

        try {
            const prodId = this.state.contextProduct ? this.state.contextProduct.id : null;
            const res = await rpc("/qba_ai/conversation/send_message", {
                conversation_id: this.state.conversationId,
                content: text,
                context_product_id: prodId,
            });

            if (res.success && res.data) {
                this._applyConversationData(res.data);
            } else {
                this.state.errorMessage = res.error || "Có lỗi xảy ra khi xử lý tin nhắn.";
                // Thông báo lỗi
                this.state.messages.push({
                    id: "error_" + Date.now(),
                    role: "assistant",
                    message_type: "error",
                    content: "⚠️ **Rất tiếc, đã có lỗi xảy ra:** " + (res.error || "Vui lòng thử lại."),
                    create_date: new Date().toLocaleTimeString(),
                    matched_products: [],
                    explanation_html: "",
                    perf_info: {},
                });
            }
        } catch (e) {
            this.state.errorMessage = "Lỗi kết nối máy chủ: " + (e.message || e);
            this.state.messages.push({
                id: "error_" + Date.now(),
                role: "assistant",
                message_type: "error",
                content: "⚠️ Không thể kết nối tới máy chủ Odoo. Vui lòng kiểm tra lại mạng hoặc thử lại.",
                create_date: new Date().toLocaleTimeString(),
                matched_products: [],
                explanation_html: "",
                perf_info: {},
            });
        } finally {
            this.state.isSending = false;
        }
    }

    /**
     * Xử lý phím tắt Enter để gửi, Shift+Enter xuống dòng
     */
    onKeyDown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.onSendMessage();
        }
    }

    /**
     * Click gợi ý nhanh (Quick prompt chips)
     */
    onSelectPrompt(promptText) {
        this.state.inputValue = promptText;
        this.onSendMessage();
    }

    /**
     * Xem chi tiết sản phẩm trong Odoo
     */
    onOpenProductDetail(productId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "product.template",
            res_id: productId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    /**
     * Yêu cầu tìm phụ tùng thay thế cho sản phẩm này
     */
    onFindSubstitutes(product) {
        const query = `Tìm phụ tùng thay thế cho ${product.default_code || product.name}`;
        this.state.inputValue = query;
        this.onSendMessage();
    }

    /**
     * So sánh sản phẩm này
     */
    onCompareProduct(product) {
        const query = `So sánh với ${product.default_code || product.name}`;
        this.state.inputValue = query;
        this.onSendMessage();
    }

    /**
     * Cập nhật dữ liệu hội thoại từ server vào reactive state
     */
    _applyConversationData(data) {
        if (!data) return;
        this.state.conversationId = data.conversation_id;
        this.state.conversationName = data.name || "Hội thoại mới";
        this.state.conversationState = data.state || "active";
        this.state.contextProduct = data.context_product || null;
        this.state.searchContext = data.search_context || {};
        this.state.messages = (data.messages || []).map((m) => ({
            ...m,
            showDetails: false, // Quản lý mở rộng bảng kỹ thuật chi tiết
        }));
    }

    /**
     * Mở modal gửi yêu cầu hỗ trợ tới Admin
     */
    openRequestModal(params = {}) {
        let query = "";
        const msg = params.message;
        if (msg) {
            const idx = this.state.messages.findIndex((m) => m.id === msg.id);
            if (idx > 0 && this.state.messages[idx - 1].role === "user") {
                query = this.state.messages[idx - 1].content;
            }
        }
        if (!query && this.state.inputValue) {
            query = this.state.inputValue.trim();
        }

        let specsSummary = "";
        if (this.state.searchContext && this.state.searchContext.specs) {
            specsSummary = Object.entries(this.state.searchContext.specs)
                .map(([k, v]) => `${v.spec_name || k}: ${v.value !== undefined ? v.value : v}${v.uom ? ' ' + v.uom : ''}`.trim())
                .join("; ");
        }

        const prod = params.product || this.state.contextProduct;

        this.state.requestForm = {
            type: params.type || "missing_product",
            query: query || "",
            productId: prod ? prod.id : null,
            productName: prod ? prod.name : "",
            productCode: prod ? (prod.default_code || "") : "",
            specsSummary: specsSummary,
            notes: "",
            messageId: msg ? msg.id : null,
        };
        this.state.requestFormError = "";
        this.state.showRequestModal = true;
    }

    /**
     * Đóng modal gửi yêu cầu
     */
    closeRequestModal() {
        this.state.showRequestModal = false;
        this.state.requestFormError = "";
    }

    /**
     * Gửi yêu cầu tới Admin qua backend RPC
     */
    async submitRequest() {
        if (this.state.isSubmittingRequest) return;
        this.state.requestFormError = "";
        this.state.isSubmittingRequest = true;

        try {
            const form = this.state.requestForm;
            const res = await rpc("/qba_ai/request/submit", {
                conversation_id: this.state.conversationId,
                message_id: form.messageId,
                request_type: form.type,
                raw_query: form.query,
                product_id: form.productId,
                extracted_specs: this.state.searchContext ? this.state.searchContext.specs : null,
                user_notes: form.notes,
            });

            if (res.success && res.data) {
                this.notificationService.add(
                    `Đã gửi yêu cầu tới Admin thành công (Mã: ${res.data.request_name}).`,
                    { type: "success" }
                );
                if (res.data.conversation_data) {
                    this._applyConversationData(res.data.conversation_data);
                }
                this.closeRequestModal();
            } else {
                this.state.requestFormError = res.error || "Không thể gửi yêu cầu hỗ trợ. Vui lòng thử lại.";
            }
        } catch (e) {
            this.state.requestFormError = "Lỗi kết nối máy chủ: " + (e.message || e);
        } finally {
            this.state.isSubmittingRequest = false;
        }
    }

    /**
     * Toggle bảng đối chiếu chi tiết trong tin nhắn
     */
    toggleMessageDetails(msg) {
        msg.showDetails = !msg.showDetails;
    }

    /**
     * Trả về Markup an toàn cho bảng đối chiếu kỹ thuật chi tiết để Owl t-out render thành HTML DOM thực sự
     */
    getExplanationMarkup(msg) {
        if (!msg || !msg.explanation_html) {
            return "";
        }
        return markup(msg.explanation_html);
    }

    /**
     * Render câu trả lời của Trợ lý QBA AI với đầy đủ định dạng (Markdown, Bảng, Danh sách, Thẻ HTML an toàn).
     * Tuyệt đối bảo đảm an toàn XSS qua DOM sanitization và chuyển đổi sang Owl Markup.
     */
    formatAssistantMessage(msg) {
        if (!msg || !msg.content) {
            return "";
        }
        let text = String(msg.content);

        // 1. Giải mã entity HTML bị escape nếu có (&lt;div..., &lt;table...)
        if (text.includes("&lt;") && /&lt;(div|table|tr|td|th|p|span|b|i|strong|em|ul|ol|li|code|hr|br|h[1-6]|alert)/i.test(text)) {
            text = text
                .replace(/&lt;/g, "<")
                .replace(/&gt;/g, ">")
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'")
                .replace(/&amp;/g, "&");
        }

        // 2. Chuyển đổi khối mã (code block)
        text = text.replace(/```([\s\S]*?)```/g, '<pre class="bg-light p-2 rounded border small"><code>$1</code></pre>');

        // 3. Chuyển đổi mã nội dòng (inline code)
        text = text.replace(/`([^`\n]+)`/g, '<code class="bg-light px-1 py-0 rounded text-dark border font-monospace" style="font-size: 0.85em;">$1</code>');

        // 4. Chuyển đổi in đậm và in nghiêng markdown
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');

        // 5. Chuyển đổi danh sách gạch đầu dòng (bullet lists) và danh sách có thứ tự (numbered lists)
        const lines = text.split("\n");
        const blocks = [];
        let currentLines = [];
        let inList = null;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();
            const ulMatch = line.match(/^(\s*)[-*]\s+(.+)$/);
            const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);

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

        // 6. Ghép thành các khối HTML có khoảng cách chuẩn
        const htmlParts = [];
        for (const b of blocks) {
            if (b.type === "ul") {
                const items = b.lines.map(l => `<li class="mb-1">${l}</li>`).join("");
                htmlParts.push(`<ul class="mb-2 ps-3">${items}</ul>`);
            } else if (b.type === "ol") {
                const items = b.lines.map(l => `<li class="mb-1">${l}</li>`).join("");
                htmlParts.push(`<ol class="mb-2 ps-3">${items}</ol>`);
            } else {
                const joined = b.lines.join("\n").trim();
                if (!joined) continue;
                if (/^<(div|table|p|blockquote|pre|h[1-6])/i.test(joined)) {
                    htmlParts.push(joined);
                } else {
                    htmlParts.push(`<p class="mb-2">${joined.replace(/\n/g, "<br/>")}</p>`);
                }
            }
        }

        const rawHtml = htmlParts.join("");
        const sanitized = this._sanitizeHtml(rawHtml);
        return markup(sanitized);
    }

    /**
     * Làm sạch HTML an toàn bằng DOMParser gốc của trình duyệt, ngăn chặn hoàn toàn XSS
     */
    _sanitizeHtml(html) {
        if (!html) return "";
        if (typeof window === "undefined" || !window.DOMParser) {
            return html;
        }
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");

        const allowedTags = new Set([
            "A", "B", "BLOCKQUOTE", "BR", "CODE", "DIV", "EM", "H1", "H2", "H3", "H4", "H5", "H6",
            "HR", "I", "LI", "OL", "P", "PRE", "SMALL", "SPAN", "STRONG", "SUB", "SUP",
            "TABLE", "TBODY", "TD", "TFOOT", "TH", "THEAD", "TR", "U", "UL"
        ]);

        const allowedAttrs = new Set([
            "class", "id", "style", "title", "target", "href", "colspan", "rowspan", "align", "valign"
        ]);

        function cleanNode(node) {
            const children = Array.from(node.childNodes);
            for (const child of children) {
                if (child.nodeType === Node.ELEMENT_NODE) {
                    const tagName = child.tagName.toUpperCase();
                    if (!allowedTags.has(tagName)) {
                        while (child.firstChild) {
                            node.insertBefore(child.firstChild, child);
                        }
                        node.removeChild(child);
                        continue;
                    }
                    const attrs = Array.from(child.attributes);
                    for (const attr of attrs) {
                        const attrName = attr.name.toLowerCase();
                        if (!allowedAttrs.has(attrName) || attrName.startsWith("on")) {
                            child.removeAttribute(attr.name);
                        } else if (attrName === "href") {
                            const val = attr.value.trim().toLowerCase();
                            if (val.startsWith("javascript:") || val.startsWith("data:")) {
                                child.removeAttribute(attr.name);
                            }
                        }
                    }
                    cleanNode(child);
                }
            }
        }

        cleanNode(doc.body);
        return doc.body.innerHTML;
    }

    /**
     * Xác định tin nhắn của AI có phải là kết quả tìm kiếm không thấy sản phẩm (để hiển thị nút Gửi Admin)
     */
    shouldShowRequestCta(msg) {
        if (!msg || msg.role !== "assistant") return false;

        // Nếu cuộc hội thoại đã gửi yêu cầu và có tin nhắn xác nhận tiếp theo, ẩn CTA trên các tin nhắn trước
        const messages = this.state.messages || [];
        const msgIdx = messages.indexOf(msg);
        if (msgIdx !== -1) {
            const hasSubsequentConfirmation = messages.slice(msgIdx + 1).some(
                m => m.message_type === "request_confirmation" || (m.content && m.content.includes("Yêu cầu hỗ trợ đã được gửi"))
            );
            if (hasSubsequentConfirmation) {
                return false;
            }
        }

        // 1. Kiểm tra dựa trên metadata rõ ràng (Explicit Response Metadata)
        if (msg.message_type) {
            return msg.message_type === "search_empty";
        }
        // 2. Fallback tương thích ngược an toàn cho các bản ghi cũ
        const text = msg.content || "";
        if (
            text.includes("Yêu cầu hỗ trợ đã được gửi") ||
            text.includes("Mã yêu cầu:") ||
            text.includes("Xin chào! Tôi là") ||
            text.startsWith("⚠️")
        ) {
            return false;
        }
        if (msg.matched_products && msg.matched_products.length > 0) {
            return false;
        }
        return (
            text.includes("Không tìm thấy") ||
            text.includes("chưa có sản phẩm") ||
            text.includes("Rất tiếc")
        );
    }
}

// 1. Đăng ký Drawer vào main_components container (gắn toàn cục không phụ thuộc XPath)
registry.category("main_components").add("QbaAiAssistantDrawer", {
    Component: QbaAiAssistantDrawer,
});

// 2. Đăng ký Client Action để các nút Action/Menu có thể mở Drawer kèm product context
registry.category("actions").add("qba_ai_assistant_open", async (env, action) => {
    env.bus.trigger("QBA_AI_OPEN_DRAWER", action.params || {});
});

