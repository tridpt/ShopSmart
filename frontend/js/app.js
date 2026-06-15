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
    if (viewName === 'settings' && typeof Settings !== 'undefined') Settings.load();

    // Close mobile sidebar
    document.getElementById('sidebar').classList.remove('open');
}

let _appModulesReady = false;
let _notifTimer = null;

/** Initialise app modules. Runs once, only after authentication. */
function onAuthenticated() {
    if (_appModulesReady) {
        // Already initialised (e.g. re-login in same tab) — just refresh data.
        Dashboard.refresh();
        Notifications.refresh();
        return;
    }
    _appModulesReady = true;

    // Init modules
    Chat.init();
    Dashboard.init();
    Notifications.init();
    Search.init();
    if (typeof Settings !== 'undefined') Settings.init();

    // Health check
    checkApiStatus();

    // Periodic refresh
    if (!_notifTimer) {
        _notifTimer = setInterval(() => {
            if (Auth.isLoggedIn()) Notifications.refresh();
        }, 30000);
    }
}

// ── Initialize ────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
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

    // Gate everything behind authentication.
    const ok = await Auth.init();
    if (ok) onAuthenticated();
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
