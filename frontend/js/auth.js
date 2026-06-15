/**
 * ShopSmart AI — Frontend Auth (login / register / session)
 */
const Auth = {
    user: null,

    isLoggedIn() {
        return !!API.getToken();
    },

    /** Called on app start. Resolves true if a valid session exists. */
    async init() {
        this._bindForm();
        if (!this.isLoggedIn()) {
            this.showAuthScreen();
            return false;
        }
        try {
            const data = await API.getMe();
            if (data && data.user) {
                this.user = data.user;
                this.hideAuthScreen();
                this._renderUser();
                return true;
            }
        } catch (e) {
            console.warn('Auth init failed:', e);
        }
        this.showAuthScreen();
        return false;
    },

    showAuthScreen() {
        const el = document.getElementById('auth-overlay');
        if (el) el.style.display = 'flex';
    },

    hideAuthScreen() {
        const el = document.getElementById('auth-overlay');
        if (el) el.style.display = 'none';
    },

    _renderUser() {
        const nameEl = document.getElementById('current-user-name');
        if (nameEl && this.user) nameEl.textContent = this.user.display_name || this.user.email;
    },

    _setError(msg) {
        const err = document.getElementById('auth-error');
        if (err) {
            err.textContent = msg || '';
            err.style.display = msg ? 'block' : 'none';
        }
    },

    _mode: 'login',

    toggleMode() {
        this._mode = this._mode === 'login' ? 'register' : 'login';
        const isLogin = this._mode === 'login';
        document.getElementById('auth-title').textContent = isLogin ? 'Đăng nhập' : 'Đăng ký';
        document.getElementById('auth-submit').textContent = isLogin ? 'Đăng nhập' : 'Tạo tài khoản';
        document.getElementById('auth-name-group').style.display = isLogin ? 'none' : 'block';
        document.getElementById('auth-toggle-text').innerHTML = isLogin
            ? 'Chưa có tài khoản? <a href="#" id="auth-toggle">Đăng ký</a>'
            : 'Đã có tài khoản? <a href="#" id="auth-toggle">Đăng nhập</a>';
        this._setError('');
        this._bindToggle();
    },

    _bindToggle() {
        const t = document.getElementById('auth-toggle');
        if (t) t.addEventListener('click', (e) => { e.preventDefault(); this.toggleMode(); });
    },

    _bindForm() {
        const form = document.getElementById('auth-form');
        if (!form || form._bound) return;
        form._bound = true;
        form.addEventListener('submit', (e) => { e.preventDefault(); this.submit(); });
        this._bindToggle();

        const logoutBtn = document.getElementById('btn-logout');
        if (logoutBtn) logoutBtn.addEventListener('click', () => this.logout());
    },

    async submit() {
        const email = (document.getElementById('auth-email').value || '').trim();
        const password = document.getElementById('auth-password').value || '';
        const displayName = (document.getElementById('auth-name').value || '').trim();
        this._setError('');

        if (!email || !password) {
            this._setError('Vui lòng nhập email và mật khẩu.');
            return;
        }

        const submitBtn = document.getElementById('auth-submit');
        submitBtn.disabled = true;

        try {
            const data = this._mode === 'login'
                ? await API.loginUser(email, password)
                : await API.register(email, password, displayName);

            if (data.error) {
                this._setError(data.error);
                return;
            }
            if (data.token) {
                API.setToken(data.token);
                this.user = data.user;
                this.hideAuthScreen();
                this._renderUser();
                // (Re)initialise the app modules now that we're authenticated.
                if (typeof onAuthenticated === 'function') onAuthenticated();
            }
        } catch (e) {
            console.error('Auth submit error:', e);
            this._setError('Lỗi kết nối server.');
        } finally {
            submitBtn.disabled = false;
        }
    },

    logout() {
        API.setToken('');
        this.user = null;
        // Hard reload to clear any in-memory per-user state.
        window.location.reload();
    },
};
