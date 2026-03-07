/* OpenStream — Video Player (Video.js + HLS.js) */

let currentSessionId = null;
let positionInterval = null;

function initPlayer(config) {
    const videoEl = document.getElementById('video-player');
    const player = videojs(videoEl, {
        controls: true,
        autoplay: false,
        preload: 'auto',
        fluid: true,
        responsive: true,
    });

    if (config.directPlay) {
        // Direct play — source already set in HTML
        player.ready(() => player.play());
    } else {
        // Transcoding — need to start a session first
        const startBtn = document.getElementById('start-transcode');
        const qualitySelect = document.getElementById('quality-select');

        if (startBtn) {
            startBtn.addEventListener('click', async () => {
                startBtn.disabled = true;
                startBtn.textContent = 'Starting...';

                try {
                    const r = await fetch('/stream/transcode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            file_id: config.fileId,
                            profile: qualitySelect.value,
                            start_time: 0,
                        }),
                    });
                    const data = await r.json();
                    if (!r.ok) throw new Error(data.detail || 'Transcode failed');

                    currentSessionId = data.session_id;
                    const hlsUrl = `/stream/hls/${data.session_id}/playlist.m3u8`;

                    if (Hls.isSupported()) {
                        const hls = new Hls({
                            maxBufferLength: 30,
                            maxMaxBufferLength: 60,
                        });
                        hls.loadSource(hlsUrl);
                        hls.attachMedia(videoEl);
                        hls.on(Hls.Events.MANIFEST_PARSED, () => player.play());
                    } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
                        // Safari native HLS
                        player.src({ src: hlsUrl, type: 'application/vnd.apple.mpegurl' });
                        player.play();
                    }

                    startBtn.style.display = 'none';
                    qualitySelect.style.display = 'none';
                } catch (e) {
                    startBtn.disabled = false;
                    startBtn.textContent = 'Retry';
                    console.error('Transcode start failed:', e);
                }
            });
        }
    }

    // Track watch position
    positionInterval = setInterval(() => {
        if (!player.paused() && player.currentTime() > 0) {
            savePosition(config.itemId, Math.floor(player.currentTime()));
        }
    }, 10000); // Every 10 seconds

    // Save position on pause/end
    player.on('pause', () => {
        savePosition(config.itemId, Math.floor(player.currentTime()));
    });
    player.on('ended', () => {
        savePosition(config.itemId, 0, true);
    });

    // Cleanup on page leave
    window.addEventListener('beforeunload', () => {
        if (currentSessionId) {
            navigator.sendBeacon(`/stream/stop/${currentSessionId}`, '');
        }
        clearInterval(positionInterval);
    });
}

async function savePosition(itemId, positionSecs, completed = false) {
    try {
        await fetch('/api/watch-history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                media_item_id: itemId,
                position_secs: positionSecs,
                completed: completed,
            }),
        });
    } catch (e) {
        // Silently fail — not critical
    }
}
