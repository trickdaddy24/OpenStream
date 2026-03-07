/* OpenStream — Global JS */

(function () {
    const searchInput = document.getElementById('global-search');
    const searchResults = document.getElementById('search-results');
    let searchTimeout = null;

    if (!searchInput || !searchResults) return;

    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        const q = searchInput.value.trim();
        if (q.length < 2) {
            searchResults.classList.remove('active');
            return;
        }
        searchTimeout = setTimeout(async () => {
            try {
                const r = await fetch(`/api/items/search?q=${encodeURIComponent(q)}`);
                const items = await r.json();
                if (items.length === 0) {
                    searchResults.innerHTML = '<div style="padding:0.75rem;color:var(--text-muted)">No results</div>';
                } else {
                    searchResults.innerHTML = items.map(item =>
                        `<a href="/item/${item.id}">${item.title}${item.year ? ' (' + item.year + ')' : ''}</a>`
                    ).join('');
                }
                searchResults.classList.add('active');
            } catch (e) {
                searchResults.classList.remove('active');
            }
        }, 300);
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.remove('active');
        }
    });
})();
