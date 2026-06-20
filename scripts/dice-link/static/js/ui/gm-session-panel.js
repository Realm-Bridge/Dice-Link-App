/**
 * GM Session Panel
 * Countdown timer for the identity panel slot when the local user is GM.
 * Renders into #identity-panel. Only initialises once per page load.
 */

let _gmPanelInitialized = false;
let _sessionTimer = null;

function initGMSessionPanel() {
    if (_gmPanelInitialized) return;
    _gmPanelInitialized = true;

    const container = document.getElementById('identity-panel');
    if (!container) return;

    _renderGMSetup(container);
}

function _renderGMSetup(container) {
    container.innerHTML = `
        <div class="gm-timer-setup">
            <span class="gm-timer-label">Session Length</span>
            <div class="gm-timer-inputs">
                <div class="gm-timer-field">
                    <input type="number" id="gm-hours" class="gm-timer-input" value="3" min="0" max="9">
                    <span class="gm-timer-unit">HRS</span>
                </div>
                <span class="gm-timer-colon">:</span>
                <div class="gm-timer-field">
                    <input type="number" id="gm-minutes" class="gm-timer-input" value="00" min="0" max="59">
                    <span class="gm-timer-unit">MIN</span>
                </div>
            </div>
            <button id="gm-start-btn" class="gm-timer-start-btn">Start Session</button>
        </div>
    `;

    document.getElementById('gm-start-btn').addEventListener('click', () => {
        const h = parseInt(document.getElementById('gm-hours').value) || 0;
        const m = parseInt(document.getElementById('gm-minutes').value) || 0;
        const total = h * 3600 + m * 60;
        if (total <= 0) return;
        _startGMCountdown(container, total);
    });
}

function _startGMCountdown(container, totalSeconds) {
    let remaining = totalSeconds;

    container.innerHTML = `
        <div class="gm-timer-running">
            <span class="gm-timer-label">Session</span>
            <span class="gm-timer-countdown" id="gm-countdown">${_formatGMTime(remaining)}</span>
        </div>
    `;

    _sessionTimer = setInterval(() => {
        remaining -= 1;
        const el = document.getElementById('gm-countdown');
        if (remaining <= 0) {
            clearInterval(_sessionTimer);
            _sessionTimer = null;
            if (el) {
                el.textContent = "Time's Up!";
                el.classList.add('gm-timer-expired');
            }
        } else {
            if (el) el.textContent = _formatGMTime(remaining);
        }
    }, 1000);
}

function _formatGMTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
