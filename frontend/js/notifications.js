/**
 * ShopSmart AI — Notifications Logic
 */
const Notifications = {
    init() {
        document.getElementById('btn-mark-read').addEventListener('click', () => this.markAllRead());
        this.refresh();
    },

    async refresh() {
        try {
            const data = await API.getNotifications();
            const notifs = data.notifications || [];
            const unread = data.unread_count || 0;

            // Update badge
            const badge = document.getElementById('notif-badge');
            if (unread > 0) {
                badge.textContent = unread;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }

            // Render list
            const list = document.getElementById('notifications-list');
            if (notifs.length === 0) {
                list.innerHTML = `<div class="empty-state"><i class="fas fa-bell-slash"></i><h3>Chưa có thông báo</h3><p>Bạn sẽ nhận thông báo khi giá sản phẩm thay đổi.</p></div>`;
                return;
            }

            list.innerHTML = notifs.map(n => {
                const iconClass = n.type || 'info';
                const icons = { deal: 'fa-fire', tracking: 'fa-crosshairs', alert: 'fa-exclamation-triangle', info: 'fa-info-circle' };
                const icon = icons[iconClass] || icons.info;
                const unreadClass = n.is_read ? '' : 'unread';
                const time = new Date(n.created_at).toLocaleString('vi-VN');

                return `
                    <div class="notif-card ${unreadClass} animate-fade-in">
                        <div class="notif-icon ${iconClass}"><i class="fas ${icon}"></i></div>
                        <div class="notif-body">
                            <div class="notif-title">${n.title}</div>
                            <div class="notif-message">${n.message}</div>
                            <div class="notif-time">${time}</div>
                        </div>
                    </div>`;
            }).join('');
        } catch (e) { /* ignore */ }
    },

    async markAllRead() {
        try {
            await API.markNotificationsRead();
            this.refresh();
        } catch (e) { /* ignore */ }
    }
};
