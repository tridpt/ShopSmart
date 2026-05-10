/**
 * ShopSmart AI — Chat Interface Logic
 */
const Chat = {
    messagesEl: null,
    inputEl: null,
    sendBtn: null,
    isProcessing: false,

    init() {
        this.messagesEl = document.getElementById('chat-messages');
        this.inputEl = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('btn-send');

        // Input events
        this.inputEl.addEventListener('input', () => this.onInputChange());
        this.inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.sendBtn.addEventListener('click', () => this.sendMessage());

        // Quick action buttons
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const msg = btn.dataset.msg;
                this.inputEl.value = msg;
                this.sendMessage();
            });
        });

        // Clear chat
        document.getElementById('btn-clear-chat').addEventListener('click', () => {
            this.clearChat();
        });

        // Load history
        this.loadHistory();
    },

    onInputChange() {
        const hasText = this.inputEl.value.trim().length > 0;
        this.sendBtn.disabled = !hasText || this.isProcessing;
        // Auto-resize
        this.inputEl.style.height = 'auto';
        this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 120) + 'px';
    },

    async sendMessage() {
        const text = this.inputEl.value.trim();
        if (!text || this.isProcessing) return;

        // Clear welcome
        const welcome = this.messagesEl.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        // Show user message
        this.appendMessage('user', text);
        this.inputEl.value = '';
        this.inputEl.style.height = 'auto';
        this.sendBtn.disabled = true;
        this.isProcessing = true;

        // Show typing
        this.showTyping();

        try {
            const data = await API.sendMessage(text);
            this.hideTyping();

            // Show assistant message with tool calls
            this.appendMessage('assistant', data.response, data.tool_calls);

            // Refresh dashboard data
            if (typeof Dashboard !== 'undefined') Dashboard.refresh();
            if (typeof Notifications !== 'undefined') Notifications.refresh();

        } catch (err) {
            this.hideTyping();
            this.appendMessage('assistant', '❌ Không thể kết nối đến server. Hãy kiểm tra lại.');
        }

        this.isProcessing = false;
        this.onInputChange();
    },

    appendMessage(role, content, toolCalls = []) {
        const div = document.createElement('div');
        div.className = `message ${role}`;

        const avatar = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

        let toolHtml = '';
        if (toolCalls && toolCalls.length > 0) {
            const chips = toolCalls.map(tc =>
                `<span class="tool-chip"><i class="fas fa-wrench"></i> ${tc.tool}</span>`
            ).join('');
            toolHtml = `<div class="tool-calls">${chips}</div>`;
        }

        // Parse markdown for assistant messages
        let htmlContent = content;
        if (role === 'assistant' && typeof marked !== 'undefined') {
            try {
                htmlContent = marked.parse(content);
            } catch (e) {
                htmlContent = content.replace(/\n/g, '<br>');
            }
        } else {
            htmlContent = content.replace(/\n/g, '<br>');
        }

        div.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">${htmlContent}${toolHtml}</div>
        `;

        this.messagesEl.appendChild(div);
        this.scrollToBottom();
    },

    showTyping() {
        const div = document.createElement('div');
        div.className = 'typing-indicator';
        div.id = 'typing';
        div.innerHTML = `
            <div class="message-avatar" style="background:var(--bg-surface);color:var(--accent-purple);border:1px solid var(--border-color)">
                <i class="fas fa-robot"></i>
            </div>
            <div>
                <div class="typing-dots"><span></span><span></span><span></span></div>
                <div class="typing-label">ShopSmart đang suy nghĩ...</div>
            </div>
        `;
        this.messagesEl.appendChild(div);
        this.scrollToBottom();
    },

    hideTyping() {
        const el = document.getElementById('typing');
        if (el) el.remove();
    },

    scrollToBottom() {
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    },

    async loadHistory() {
        try {
            const data = await API.getChatHistory();
            if (data.history && data.history.length > 0) {
                const welcome = this.messagesEl.querySelector('.welcome-message');
                if (welcome) welcome.remove();

                data.history.forEach(msg => {
                    this.appendMessage(msg.role, msg.content);
                });
            }
        } catch (e) { /* ignore */ }
    },

    async clearChat() {
        if (!confirm('Xóa toàn bộ lịch sử chat?')) return;
        try {
            await API.clearChat();
            this.messagesEl.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon"><i class="fas fa-shopping-cart"></i></div>
                    <h3>Xin chào! Tôi là ShopSmart AI 🛒</h3>
                    <p>Tôi có thể giúp bạn tìm kiếm sản phẩm, so sánh giá, và theo dõi deal tốt.</p>
                    <div class="quick-actions">
                        <button class="quick-btn" data-msg="Tìm iPhone 16 giá tốt nhất"><i class="fas fa-mobile-alt"></i> Tìm iPhone 16</button>
                        <button class="quick-btn" data-msg="So sánh giá laptop gaming dưới 20 triệu"><i class="fas fa-laptop"></i> Laptop gaming</button>
                        <button class="quick-btn" data-msg="Tìm tai nghe bluetooth giá rẻ chất lượng"><i class="fas fa-headphones"></i> Tai nghe BT</button>
                        <button class="quick-btn" data-msg="Xem sản phẩm đang theo dõi"><i class="fas fa-list"></i> Đang theo dõi</button>
                    </div>
                </div>`;
            // Rebind quick buttons
            document.querySelectorAll('.quick-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.inputEl.value = btn.dataset.msg;
                    this.sendMessage();
                });
            });
        } catch (e) { /* ignore */ }
    }
};
