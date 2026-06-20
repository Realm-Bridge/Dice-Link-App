/**
 * Player Portrait Panel
 * Renders the character portrait into #identity-panel for non-GM users.
 * Only initialises once per page load.
 */

let _playerPortraitInitialized = false;

function setPortraitVisible(visible) {
    const panel = document.querySelector('.player-portrait-panel');
    if (panel) panel.style.display = visible ? '' : 'none';
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
        <div class="player-portrait-frame">
            ${frameContent}
        </div>
        ${characterName ? `<span class="player-portrait-name">${escapeHtml(characterName)}</span>` : ''}
    `;

    container.appendChild(panel);
}
