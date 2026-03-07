/* OpenStream — Video Player (Video.js + HLS.js)
 *
 * Supports four playback modes (Plex-style hierarchy):
 *   direct_play     — MP4 served as-is (zero CPU)
 *   direct_stream   — MKV remuxed to HLS with -c copy (near-zero CPU)
 *   audio_transcode — video copied, audio transcoded to AAC (light CPU)
 *   full_transcode  — full HLS transcode with quality presets
 */

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

    var mode = config.playbackMode || (config.directPlay ? 'direct_play' : 'full_transcode');

    if (mode === 'direct_play') {
        // ──── Direct Play ────
        // File is browser-ready (MP4 + H.264 + AAC). Serve as-is.
        player.src({
            src: '/stream/direct/' + config.fileId,
            type: 'video/mp4',
        });
        player.ready(function () {
            console.log('[Player] Direct Play ready for file', config.fileId);
        });

    } else if (mode === 'direct_stream' || mode === 'audio_transcode') {
        // ──── Direct Stream / Audio Transcode ────
        // Automatically start HLS with copy profile (no quality picker).
        // direct_stream  → remux profile (-c:v copy -c:a copy)
        // audio_transcode → audio_transcode profile (-c:v copy -c:a aac)
        var profileName = (mode === 'direct_stream') ? 'remux' : 'audio_transcode';
        console.log('[Player] Auto-starting', mode, 'with profile:', profileName);

        _startHlsSession(player, config, profileName, errorDiv);

    } else {
        // ──── Full Transcode ────
        // User picks quality and clicks "Start Playback".
        var startBtn = document.getElementById('start-transcode');
        var qualitySelect = document.getElementById('quality-select');

        if (startBtn) {
            startBtn.addEventListener('click', async function () {
                startBtn.disabled = true;
                startBtn.textContent = 'Starting transcode...';
                if (errorDiv) errorDiv.style.display = 'none';

                _startHlsSession(player, config, qualitySelect.value, errorDiv)
                    .then(function () {
                        startBtn.style.display = 'none';
                        if (qualitySelect) qualitySelect.parentElement.style.display = 'none';
                    })
                    .catch(function (e) {
                        console.error('Transcode start failed:', e);
                        startBtn.disabled = false;
                        startBtn.textContent = 'Retry';
                        if (errorDiv) {
                            errorDiv.textContent = 'Transcode failed: ' + e.message;
                            errorDiv.style.display = 'block';
                        }
                    });
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


/**
 * Start an HLS transcode/remux session and load it into the player.
 * Works for all non-direct-play modes (remux, audio_transcode, full).
 */
async function _startHlsSession(player, config, profileName, errorDiv) {
    var r = await fetch('/stream/transcode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            file_id: config.fileId,
            profile: profileName,
            start_time: 0,
        }),
    });
    var data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Transcode request failed');

    currentSessionId = data.session_id;
    var hlsUrl = '/stream/hls/' + data.session_id + '/playlist.m3u8';
    console.log('[Player] HLS session started:', data.session_id, 'profile:', profileName);

    _loadHls(player, hlsUrl);
}


function _loadHls(player, hlsUrl) {
    // Get the underlying <video> DOM element from Video.js
    var videoElement = player.tech({ IWillNotUseThisInPlugins: true }).el();

    if (typeof Hls !== 'undefined' && Hls.isSupported()) {
        // Use HLS.js (Chrome, Firefox, Edge)
        var hls = new Hls({
            liveSyncDurationCount: 3,      // Stay 3 segments behind live edge
            liveMaxLatencyDurationCount: 6,
            maxBufferLength: 60,           // Buffer up to 60s ahead
            maxMaxBufferLength: 120,       // Allow up to 120s in good conditions
            maxBufferHole: 0.5,            // Tolerate small gaps
            startLevel: -1,
            fragLoadingTimeOut: 20000,     // 20s timeout per segment (transcoding can be slow)
            fragLoadingMaxRetry: 6,        // Retry segments up to 6 times
            fragLoadingRetryDelay: 1000,   // 1s between retries
            levelLoadingTimeOut: 15000,    // 15s timeout for playlist reload
            levelLoadingMaxRetry: 4,
        });
        hls.loadSource(hlsUrl);
        hls.attachMedia(videoElement);

        hls.on(Hls.Events.MANIFEST_PARSED, function () {
            console.log('[Player] HLS manifest parsed, starting playback');
            player.play().catch(function (e) {
                console.warn('[Player] Autoplay blocked:', e.message);
            });
        });

        hls.on(Hls.Events.ERROR, function (event, data) {
            console.error('[Player] HLS.js error:', data.type, data.details, data);
            if (data.fatal) {
                var errorDiv = document.getElementById('player-error');
                if (errorDiv) {
                    errorDiv.textContent = 'HLS error: ' + data.details;
                    errorDiv.style.display = 'block';
                }
                if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                    console.log('[Player] Attempting HLS network recovery...');
                    hls.startLoad();
                } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                    console.log('[Player] Attempting HLS media error recovery...');
                    hls.recoverMediaError();
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
            console.warn('[Player] Autoplay blocked:', e.message);
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
