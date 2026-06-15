/**
 * ShopSmart AI — Direct Search (No AI needed)
 */
const Search = {
    inputEl: null,
    btnEl: null,
    resultsEl: null,
    statusEl: null,
    isSearching: false,

    init() {
        this.inputEl = document.getElementById('search-input');
        this.btnEl = document.getElementById('btn-search');
        this.resultsEl = document.getElementById('search-results');
        this.statusEl = document.getElementById('search-status');

        if (!this.btnEl) return;

        this.compareBtnEl = document.getElementById('btn-compare');
        this.btnEl.addEventListener('click', () => this.doSearch());
        if (this.compareBtnEl) {
            this.compareBtnEl.addEventListener('click', () => this.doCompare());
        }
        this.inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.doSearch();
        });

        // Tag buttons
        document.querySelectorAll('.search-tag').forEach(tag => {
            tag.addEventListener('click', () => {
                this.inputEl.value = tag.dataset.q;
                this.doSearch();
            });
        });
    },

    async doSearch() {
        const query = this.inputEl.value.trim();
        if (!query || this.isSearching) return;

        this.isSearching = true;
        this.btnEl.disabled = true;
        this.btnEl.textContent = 'Đang tìm...';

        // Show loading
        this.statusEl.style.display = 'flex';
        this.statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang tìm trên Shopee, Tiki, CellphoneS, FPT Shop, TGDĐ, Lazada...';

        // Show skeleton cards
        this.resultsEl.innerHTML = Array(6).fill('<div class="product-skeleton"></div>').join('');

        try {
            const data = await API.get(`/api/search?q=${encodeURIComponent(query)}`);

            if (data.error) {
                this.statusEl.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.error}`;
                this.resultsEl.innerHTML = '';
            } else {
                this.renderResults(data, query);
            }
        } catch (err) {
            this.statusEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> Lỗi kết nối server';
            this.resultsEl.innerHTML = '';
        }

        this.isSearching = false;
        this.btnEl.disabled = false;
        this.btnEl.textContent = 'Tìm kiếm';
    },

    renderResults(data, query) {
        const results = data.results || [];
        const sources = data.sources_found || [];

        // Status bar
        if (results.length === 0) {
            this.statusEl.innerHTML = `<i class="fas fa-info-circle"></i> Không tìm thấy kết quả cho "${query}". Thử từ khóa khác.`;
            this.resultsEl.innerHTML = '';
            return;
        }

        let statusHtml = `<i class="fas fa-check-circle"></i> Tìm thấy <strong>${results.length}</strong> kết quả cho "${query}"`;
        if (sources.length > 0) {
            statusHtml += ` &mdash; Nguồn: ${sources.join(', ')}`;
        }
        this.statusEl.innerHTML = statusHtml;

        // Keep results around so the track action can read them by index.
        this._results = results;

        // Render product cards
        this.resultsEl.innerHTML = results.map((r, i) => {
            const source = r.source || 'Web';
            const badgeClass = this._sourceBadgeClass(source);
            const snippet = r.snippet
                ? `<div class="product-snippet">${r.snippet}</div>`
                : '';
            const viewBtn = r.url
                ? `<a href="${r.url}" target="_blank" rel="noopener" class="btn-visit"><i class="fas fa-external-link-alt"></i> Xem trên ${source}</a>`
                : '';
            const priceBtn = r.url
                ? `<button class="btn-check-price" onclick="Search.fetchPrice('${r.url}', ${i})" id="price-btn-${i}"><i class="fas fa-tag"></i> Xem giá</button>`
                : '';

            return `
                <div class="product-card">
                    <div class="product-header">
                        <span class="product-source-badge ${badgeClass}">${source}</span>
                        <div class="product-name">${r.product_name || 'Sản phẩm'}</div>
                    </div>
                    ${snippet}
                    <div class="product-price-display" id="price-display-${i}"></div>
                    <div class="product-footer">
                        <div class="product-actions">
                            ${priceBtn}
                            ${viewBtn}
                        </div>
                        <div class="track-row">
                            <input type="number" min="0" step="1000" class="track-target-input"
                                   id="track-target-${i}" placeholder="Giá mục tiêu (đ) — tùy chọn">
                            <button class="btn-track" id="track-btn-${i}" onclick="Search.trackProduct(${i})">
                                <i class="fas fa-bell"></i> Theo dõi
                            </button>
                        </div>
                    </div>
                </div>`;
        }).join('');
    },

    async doCompare() {
        const query = this.inputEl.value.trim();
        if (!query || this.isSearching) return;

        this.isSearching = true;
        if (this.compareBtnEl) this.compareBtnEl.disabled = true;
        this.btnEl.disabled = true;

        this.statusEl.style.display = 'flex';
        this.statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang so sánh giá từ các sàn (có thể mất vài giây)...';
        this.resultsEl.innerHTML = Array(4).fill('<div class="product-skeleton"></div>').join('');

        try {
            const data = await API.compare(query);
            if (data.error) {
                this.statusEl.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.error}`;
                this.resultsEl.innerHTML = '';
            } else {
                this.renderComparison(data, query);
            }
        } catch (err) {
            console.error('Compare error:', err);
            this.statusEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> Lỗi kết nối server';
            this.resultsEl.innerHTML = '';
        }

        this.isSearching = false;
        if (this.compareBtnEl) this.compareBtnEl.disabled = false;
        this.btnEl.disabled = false;
    },

    renderComparison(data, query) {
        const offers = data.offers || [];
        if (offers.length === 0) {
            this.statusEl.innerHTML = `<i class="fas fa-info-circle"></i> Không tìm thấy sản phẩm để so sánh cho "${query}".`;
            this.resultsEl.innerHTML = '';
            return;
        }

        const cheapest = data.cheapest_source;
        let statusHtml = `<i class="fas fa-balance-scale"></i> So sánh <strong>${offers.length}</strong> nguồn cho "${query}"`;
        if (data.priced_count > 0 && cheapest) {
            statusHtml += ` &mdash; Rẻ nhất: <strong>${cheapest}</strong>`;
        } else {
            statusHtml += ' &mdash; chưa lấy được giá từ nguồn nào (trang có thể chặn bóc giá).';
        }
        this.statusEl.innerHTML = statusHtml;

        const rows = offers.map(o => {
            const badge = this._sourceBadgeClass(o.source);
            const priceCell = o.price
                ? `<span class="cmp-price">${o.price_formatted}</span>`
                : '<span class="cmp-price no-price">—</span>';
            const best = o.is_cheapest
                ? '<span class="cmp-best"><i class="fas fa-crown"></i> Rẻ nhất</span>' : '';
            const link = o.url
                ? `<a href="${o.url}" target="_blank" rel="noopener" class="cmp-link"><i class="fas fa-external-link-alt"></i> Xem</a>`
                : '';
            return `
                <div class="cmp-row ${o.is_cheapest ? 'cheapest' : ''}">
                    <span class="product-source-badge ${badge}">${o.source}</span>
                    <span class="cmp-name">${o.product_name || 'Sản phẩm'}</span>
                    ${priceCell}
                    ${best}
                    ${link}
                </div>`;
        }).join('');

        this.resultsEl.innerHTML = `<div class="compare-table">${rows}</div>`;
    },

    async trackProduct(index) {
        const r = (this._results || [])[index];
        if (!r) return;
        const btn = document.getElementById(`track-btn-${index}`);
        const targetEl = document.getElementById(`track-target-${index}`);
        const targetRaw = targetEl ? targetEl.value.trim() : '';

        // Reuse a price already fetched for this card, if any.
        const displayEl = document.getElementById(`price-display-${index}`);
        let currentPrice = null;
        if (displayEl) {
            const m = displayEl.textContent.replace(/[^\d]/g, '');
            if (m) currentPrice = Number(m);
        }

        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lưu...'; }

        try {
            const payload = {
                name: r.product_name || 'Sản phẩm',
                url: r.url || null,
                source: r.source || null,
            };
            if (currentPrice) payload.current_price = currentPrice;
            if (targetRaw) payload.target_price = Number(targetRaw);

            const data = await API.post('/api/track', payload);
            if (data.success) {
                if (btn) { btn.innerHTML = '<i class="fas fa-check"></i> Đã theo dõi'; btn.classList.add('tracked'); }
                if (typeof Dashboard !== 'undefined') Dashboard.refresh();
            } else {
                if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-bell"></i> Theo dõi'; }
                alert(data.error || 'Không thể theo dõi sản phẩm.');
            }
        } catch (e) {
            console.error('Track error:', e);
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-bell"></i> Theo dõi'; }
            alert('Lỗi kết nối khi theo dõi.');
        }
    },

    async fetchPrice(url, index) {
        const btn = document.getElementById(`price-btn-${index}`);
        const display = document.getElementById(`price-display-${index}`);
        if (!btn || !display) return;

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lấy giá...';

        try {
            const data = await API.post('/api/scrape-price', { url });

            if (data.price) {
                display.innerHTML = `<span class="product-price">${data.price_formatted || data.price}</span>`;
                btn.style.display = 'none';
            } else {
                display.innerHTML = '<span class="product-price no-price">Không lấy được giá. Xem trên trang gốc.</span>';
                btn.style.display = 'none';
            }
        } catch (err) {
            display.innerHTML = '<span class="product-price no-price">Lỗi kết nối</span>';
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-tag"></i> Thử lại';
        }
    },

    _sourceBadgeClass(source) {
        const map = {
            'Shopee': 'shopee', 'Tiki': 'tiki', 'Lazada': 'lazada',
            'CellphoneS': 'cellphones', 'FPT Shop': 'fptshop',
            'The Gioi Di Dong': 'tgdd', 'Dien May Xanh': 'dmx',
            'Hnam Mobile': 'hnam',
        };
        return map[source] || 'web';
    }
};
