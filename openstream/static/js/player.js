/* OpenStream — Video Player (Video.js + HLS.js) */

var currentSessionId = null;
var positionInterval = null;

function initPlayer(config) {
    var videoEl = document.getElementById('video-player');
    var errorDiv = document.getElementById('player-error');

    // Initialize Video.js (no data-setup on the element — we init here only)
    var player = videojs(videoEl, {
        controls: true,
        autoplay: false,
        preload: 'auto',
        fluid: true,
        responsive: true,
    });

    // Error handler — show errors visually
    player.on('error', function () {
        var err = player.error();
        var msg = err ? 'Player error: ' + (err.message || 'code ' + err.code) : 'Unknown playback error';
        console.error(msg, err);
        if (errorDiv) {
            errorDiv.textContent = msg;
            errorDiv.style.display = 'block';
        }
    });

    if (config.directPlay) {
        // Direct play — set source via Video.js API
        player.src({
            src: '/stream/direct/' + config.fileId,
            type: 'video/mp4',
        });

        // Let the user click the big play button (no autoplay — browsers block it)
        player.ready(function () {
            console.log('Direct play ready for file', config.fileId);
        });
    } else {
        // Transcoding — user must click "Start Playback"
        var startBtn = document.getElementById('start-transcode');
        var qualitySelect = document.getElementById('quality-select');

        if (startBtn) {
            startBtn.addEventListener('click', async function () {
                startBtn.disabled = true;
                startBtn.textContent = 'Starting transcode...';
                if (errorDiv) errorDiv.style.display = 'none';

                try {
                    var r = await fetch('/stream/transcode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            file_id: config.fileId,
                            profile: qualitySelect.value,
                            start_time: 0,
                        }),
                    });
                    var data = await r.json();
                    if (!r.ok) throw new Error(data.detail || 'Transcode request failed');

                    currentSessionId = data.session_id;
                    var hlsUrl = '/stream/hls/' + data.session_id + '/playlist.m3u8';
                    console.log('Transcode started, HLS URL:', hlsUrl);

                    _loadHls(player, hlsUrl);

                    startBtn.style.display = 'none';
                    if (qualitySelect) qualitySelect.parentElement.style.display = 'none';
                } catch (e) {
                    console.error('Transcode start failed:', e);
                    startBtn.disabled = false;
                    startBtn.textContent = 'Retry';
                    if (errorDiv) {
                        errorDiv.textContent = 'Transcode failed: ' + e.message;
                        errorDiv.style.display = 'block';
                    }
                }
            });
        }
    }

    // Track watch position every 10 seconds
    positionInterval = setInterval(function () {
        if (!player.paused() && player.currentTime() > 0) {
            savePosition(config.itemId, Math.floor(player.currentTime()));
        }
    }, 10000);

    // Save position on pause/end
    player.on('pause', function () {
        if (player.currentTime() > 0) {
            savePosition(config.itemId, Math.floor(player.currentTime()));
        }
    });
    player.on('ended', function () {
        savePosition(config.itemId, 0, true);
    });

    // Cleanup on page leave
    window.addEventListener('beforeunload', function () {
        if (currentSessionId) {
            navigator.sendBeacon('/stream/stop/' + currentSessionId, '');
        }
        clearInterval(positionInterval);
    });
}


function _loadHls(player, hlsUrl) {
    // Get the underlying <video> DOM element from Video.js
    var videoElement = player.tech({ IWillNotUseThisInPlugins: true }).el();

    if (typeof Hls !== 'undefined' && Hls.isSupported()) {
        // Use HLS.js (Chrome, Firefox, Edge)
        var hls = new Hls({
            maxBufferLength: 30,
            maxMaxBufferLength: 60,
            startLevel: -1,
        });
        hls.loadSource(hlsUrl);
        hls.attachMedia(videoElement);

        hls.on(Hls.Events.MANIFEST_PARSED, function () {
            console.log('HLS manifest parsed, starting playback');
            player.play().catch(function (e) {
                console.warn('Autoplay after transcode blocked:', e.message);
            });
        });

        hls.on(Hls.Events.ERROR, function (event, data) {
            console.error('HLS.js error:', data.type, data.details, data);
            if (data.fatal) {
                var errorDiv = document.getElementById('player-error');
                if (errorDiv) {
                    errorDiv.textContent = 'HLS error: ' + data.details;
                    errorDiv.style.display = 'block';
                }
                if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                    console.log('Attempting HLS recovery...');
                    hls.startLoad();
                } else {
                    hls.destroy();
                }
            }
        });
    } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
        // Safari native HLS
        player.src({
            src: hlsUrl,
            type: 'application/vnd.apple.mpegurl',
        });
        player.play().catch(function (e) {
            console.warn('Autoplay after transcode blocked:', e.message);
        });
    } else {
        var errorDiv = document.getElementById('player-error');
        if (errorDiv) {
            errorDiv.textContent = 'Your browser does not support HLS playback.';
            errorDiv.style.display = 'block';
        }
    }
}


async function savePosition(itemId, positionSecs, completed) {
    completed = completed || false;
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
