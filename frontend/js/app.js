/**
 * ShopSmart AI — Main App Controller
 */

// ── View Switching ────────────────────────────────
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const view = document.getElementById(`view-${viewName}`);
    const nav = document.querySelector(`.nav-item[data-view="${viewName}"]`);

    if (view) view.classList.add('active');
    if (nav) nav.classList.add('active');

    // Refresh data on view switch
    if (viewName === 'dashboard' || viewName === 'tracking') Dashboard.refresh();
    if (viewName === 'notifications') Notifications.refresh();

    // Close mobile sidebar
    document.getElementById('sidebar').classList.remove('open');
}

// ── Initialize ────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Nav clicks
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => switchView(btn.dataset.view));
    });

    // Mobile menu toggles
    document.querySelectorAll('.menu-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });
    });

    // Init modules
    Chat.init();
    Dashboard.init();
    Notifications.init();

    // Health check
    checkApiStatus();

    // Periodic refresh
    setInterval(() => {
        Notifications.refresh();
    }, 30000);
});

async function checkApiStatus() {
    const statusEl = document.getElementById('api-status');
    try {
        const data = await API.healthCheck();
        const dot = statusEl.querySelector('.status-dot');
        const text = statusEl.querySelector('span:last-child');

        if (data.api_key_set) {
            dot.className = 'status-dot online';
            text.textContent = 'AI sẵn sàng';
        } else {
            dot.className = 'status-dot offline';
            text.textContent = 'Thiếu API Key';
        }
    } catch (e) {
        const dot = statusEl.querySelector('.status-dot');
        const text = statusEl.querySelector('span:last-child');
        dot.className = 'status-dot offline';
        text.textContent = 'Mất kết nối';
    }
}
