/* OpenStream — Global JS */

/* ========== Search ========== */
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

/* ========== Global Scan Progress Indicator ========== */
(function () {
    const bar = document.getElementById('global-scan-bar');
    const fill = document.getElementById('global-scan-fill');
    const text = document.getElementById('global-scan-text');
    const pct = document.getElementById('global-scan-pct');

    if (!bar) return;

    let activeSse = null;

    /** Show the global scan bar and connect SSE for a library. */
    function showGlobalScan(libraryId) {
        bar.style.display = 'block';
        fill.style.width = '0%';
        text.textContent = 'Scanning...';
        pct.textContent = '';

        // Close any existing SSE connection
        if (activeSse) { activeSse.close(); activeSse = null; }

        activeSse = new EventSource('/api/scan-progress/' + libraryId);
        activeSse.onmessage = function (e) {
            var data = JSON.parse(e.data);
            if (data.event === 'progress') {
                var percent = Math.round((data.current / data.total) * 100);
                fill.style.width = percent + '%';
                text.textContent = data.title;
                pct.textContent = percent + '%';
            } else if (data.event === 'complete') {
                fill.style.width = '100%';
                text.textContent = 'Scan complete!';
                pct.textContent = '100%';
                activeSse.close();
                activeSse = null;
                // Fade out after a moment
                setTimeout(function () {
                    bar.classList.add('global-scan-bar-done');
                    setTimeout(function () {
                        bar.style.display = 'none';
                        bar.classList.remove('global-scan-bar-done');
                    }, 600);
                }, 2000);
            } else if (data.event === 'error') {
                text.textContent = 'Scan error';
                pct.textContent = '';
                activeSse.close();
                activeSse = null;
                setTimeout(function () { bar.style.display = 'none'; }, 4000);
            } else if (data.event === 'no_scan') {
                bar.style.display = 'none';
                activeSse.close();
                activeSse = null;
            }
        };
        activeSse.onerror = function () {
            activeSse.close();
            activeSse = null;
            bar.style.display = 'none';
        };
    }

    /** Hide the global scan bar. */
    function hideGlobalScan() {
        if (activeSse) { activeSse.close(); activeSse = null; }
        bar.classList.add('global-scan-bar-done');
        setTimeout(function () {
            bar.style.display = 'none';
            bar.classList.remove('global-scan-bar-done');
        }, 600);
    }

    // Expose globally so settings page can call these
    window.__showGlobalScan = showGlobalScan;
    window.__hideGlobalScan = hideGlobalScan;

    // On page load, check if any library is currently scanning
    fetch('/api/libraries')
        .then(function (r) { return r.json(); })
        .then(function (libs) {
            var scanning = libs.find(function (l) { return l.scan_status === 'scanning'; });
            if (scanning) {
                showGlobalScan(scanning.id);
            }
        })
        .catch(function () { /* silent — user may not be logged in */ });
})();
