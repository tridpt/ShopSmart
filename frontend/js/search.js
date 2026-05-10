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

        this.btnEl.addEventListener('click', () => this.doSearch());
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
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();

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
                    </div>
                </div>`;
        }).join('');
    },

    async fetchPrice(url, index) {
        const btn = document.getElementById(`price-btn-${index}`);
        const display = document.getElementById(`price-display-${index}`);
        if (!btn || !display) return;

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lấy giá...';

        try {
            const res = await fetch('/api/scrape-price', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();

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
