/**
 * ShopSmart AI — Settings (account + notification channels)
 */
const Settings = {
    _channels: { telegram: false, email: false },

    init() {
        const saveBtn = document.getElementById('btn-save-settings');
        if (saveBtn) saveBtn.addEventListener('click', () => this.save());
        // Server channel availability (whether the deployment has Telegram/SMTP configured).
        this._loadChannelStatus();
    },

    _setMsg(kind, msg) {
        const errEl = document.getElementById('settings-error');
        const okEl = document.getElementById('settings-success');
        if (errEl) errEl.style.display = 'none';
        if (okEl) okEl.style.display = 'none';
        const el = kind === 'error' ? errEl : okEl;
        if (el) {
            el.textContent = msg || '';
            el.style.display = msg ? 'block' : 'none';
        }
    },

    async _loadChannelStatus() {
        try {
            const health = await API.healthCheck();
            this._channels = health.channels || { telegram: false, email: false };
        } catch (e) {
            console.warn('Settings: health check failed', e);
        }
        this._renderChannelStatus();
    },

    _renderChannelStatus() {
        const box = document.getElementById('settings-channel-status');
        if (!box) return;
        const chip = (ok, label) =>
            `<span class="channel-chip ${ok ? 'on' : 'off'}">
                <i class="fas fa-${ok ? 'check-circle' : 'times-circle'}"></i> ${label} ${ok ? 'sẵn sàng' : 'chưa cấu hình'}
             </span>`;
        box.innerHTML =
            chip(this._channels.email, 'Email (SMTP)') +
            chip(this._channels.telegram, 'Telegram bot');

        // If the server has no Telegram bot token, the chat id field can't do anything.
        const tgField = document.getElementById('settings-telegram');
        if (tgField && !this._channels.telegram) {
            tgField.disabled = true;
            tgField.placeholder = 'Server chưa cấu hình TELEGRAM_BOT_TOKEN';
        }
        const emailStatus = document.getElementById('settings-email-status');
        if (emailStatus && !this._channels.email) {
            emailStatus.textContent = 'Server chưa cấu hình SMTP — bật cũng chưa gửi được.';
        }
    },

    /** Populate the form from the current user object (called when view opens). */
    async load() {
        this._setMsg();
        try {
            const data = await API.getMe();
            const user = (data && data.user) || {};
            const setText = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val || '—';
            };
            setText('settings-email', user.email);
            setText('settings-name', user.display_name);

            const emailToggle = document.getElementById('settings-notify-email');
            if (emailToggle) emailToggle.checked = !!user.notify_email;

            // We don't echo the stored chat id back (server returns only has_telegram),
            // but reflect whether one is set via the placeholder.
            const tgField = document.getElementById('settings-telegram');
            if (tgField && user.has_telegram) {
                tgField.placeholder = '✓ Đã lưu một chat id (nhập mới để thay đổi)';
            }
        } catch (e) {
            console.warn('Settings.load failed', e);
        }
    },

    async save() {
        this._setMsg();
        const btn = document.getElementById('btn-save-settings');
        const emailToggle = document.getElementById('settings-notify-email');
        const tgField = document.getElementById('settings-telegram');

        const payload = {};
        if (emailToggle) payload.notify_email = emailToggle.checked;
        if (tgField && !tgField.disabled) {
            const v = tgField.value.trim();
            // Only send when the user typed something, to avoid wiping an existing id by accident.
            if (v !== '') payload.telegram_chat_id = v;
        }

        if (btn) btn.disabled = true;
        try {
            const data = await API.updateSettings(payload);
            if (data && data.error) {
                this._setMsg('error', data.error);
                return;
            }
            this._setMsg('success', 'Đã lưu cài đặt thông báo.');
            if (tgField) tgField.value = '';
            await this.load();
        } catch (e) {
            console.error('Settings.save failed', e);
            this._setMsg('error', 'Lỗi kết nối khi lưu cài đặt.');
        } finally {
            if (btn) btn.disabled = false;
        }
    },
};
