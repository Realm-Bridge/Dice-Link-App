/**
 * Player Portrait Panel
 * Renders the character portrait into #identity-panel for non-GM users.
 * Only initialises once per page load.
 */

let _playerPortraitInitialized = false;

function clearPortrait() {
    const panel = document.querySelector('.player-portrait-panel');
    if (panel) panel.remove();
    _playerPortraitInitialized = false;
}

function initPlayerPortrait(selfPlayer) {
    if (_playerPortraitInitialized) return;
    _playerPortraitInitialized = true;

    const container = document.getElementById('identity-panel');
    if (!container) return;

    const portraitUrl = selfPlayer.portraitUrl || null;
    const characterName = selfPlayer.characterName || '';

    const frameContent = portraitUrl
        ? `<img class="player-portrait-img" src="${escapeHtml(portraitUrl)}" alt="">`
        : `<div class="player-portrait-placeholder"></div>`;

    const panel = document.createElement('div');
    panel.className = 'player-portrait-panel';
    panel.innerHTML = `
        <div class="player-portrait-frame-wrapper">
            <div class="player-portrait-frame">
                ${frameContent}
            </div>
        </div>
        ${characterName ? `<span class="player-portrait-name">${escapeHtml(characterName)}</span>` : ''}
    `;

    container.appendChild(panel);

    const wrapper = panel.querySelector('.player-portrait-frame-wrapper');
    const img     = panel.querySelector('.player-portrait-img');
    const frame   = panel.querySelector('.player-portrait-frame');
    const nameEl  = panel.querySelector('.player-portrait-name');

    if (img && frame && wrapper) {
        const sizeFrame = () => {
            if (!img.naturalWidth || !img.naturalHeight) return;

            const ratio  = img.naturalWidth / img.naturalHeight;
            const maxW   = wrapper.clientWidth - 40;   // 20px margin each side
            const maxH   = wrapper.clientHeight;

            let w = maxW;
            let h = w / ratio;

            if (h > maxH) {
                h = maxH;
                w = h * ratio;
            }

            frame.style.width  = w + 'px';
            frame.style.height = h + 'px';
        };

        if (img.complete && img.naturalWidth) {
            sizeFrame();
        } else {
            img.addEventListener('load', sizeFrame);
        }
    }

    if (nameEl) {
        document.fonts.ready.then(() => _fitPortraitName(nameEl));
    }
}

function _fitPortraitName(el) {
    const maxHeight = 85; // 2 lines at 34px × 1.25 line-height
    let size = 34;
    el.style.fontSize = size + 'px';
    while (el.scrollHeight > maxHeight && size > 14) {
        size--;
        el.style.fontSize = size + 'px';
    }
}
