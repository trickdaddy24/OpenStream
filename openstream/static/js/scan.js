/* OpenStream — Scan Progress (SSE listener) */

(function () {
    const bar = document.getElementById('scan-bar');
    const text = document.getElementById('scan-text');

    if (!bar || !text) return;

    // Extract library ID from URL
    const match = window.location.pathname.match(/\/scan\/(\d+)/);
    if (!match) return;

    const libraryId = match[1];
    const evtSource = new EventSource(`/api/scan-progress/${libraryId}`);

    evtSource.onmessage = (e) => {
        const data = JSON.parse(e.data);

        if (data.event === 'progress') {
            const pct = Math.round((data.current / data.total) * 100);
            bar.style.width = pct + '%';
            text.textContent = `${data.current} / ${data.total} — ${data.title}`;
        } else if (data.event === 'complete') {
            bar.style.width = '100%';
            text.textContent = 'Scan complete! Redirecting...';
            evtSource.close();
            setTimeout(() => window.location.href = '/', 1500);
        } else if (data.event === 'error') {
            text.textContent = 'Scan error: ' + (data.message || 'unknown');
            evtSource.close();
        } else if (data.event === 'no_scan') {
            text.textContent = 'No scan in progress for this library.';
            evtSource.close();
        }
    };

    evtSource.onerror = () => {
        text.textContent = 'Connection lost. Refresh to check status.';
        evtSource.close();
    };
})();
