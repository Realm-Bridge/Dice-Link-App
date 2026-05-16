/**
 * Chat Log UI Module
 * Renders incoming Foundry chat messages inside the control panel,
 * styled exclusively with Foundry's own CSS loaded into the main document.
 *
 * CSS strategy:
 *   - Foundry stylesheets loaded as @layer(foundry) so DLA's own unlayered
 *     CSS always wins any conflict — Foundry cannot break DLA's UI.
 *   - DLA's document.body carries Foundry's body classes, so body.xxx
 *     selectors in Foundry's CSS fire correctly.
 *   - Foundry's computed root font-size is applied to #vtt-chat-log so that
 *     em-based values inside chat cards compute against the correct base.
 *   - All card content styling (images, avatars, colours, fonts, layout
 *     inside cards) is left entirely to Foundry's own CSS. We add nothing
 *     system-specific here.
 *   - Our CSS only covers the outer panel structure needed to make the
 *     chat list exist and scroll inside DLA's layout.
 */

let messageList = null;
let pendingMessages = [];
let _foundryStylesInjected = false;
let _pendingSetup = null;
let _zoomObserver = null;

// ============================================================================
// CHAT SETUP — receives Foundry CSS data from DLC before chatInit
// ============================================================================

function handleChatSetup(message) {
    const bodyClasses = message.bodyClasses || [];
    debugChatLog('handleChatSetup received', {
        blocks: (message.styleTexts || []).length,
        vars: Object.keys(message.cssVars || {}).length,
        bodyClasses: bodyClasses.length,
        rootFontSize: message.rootFontSize || 'not sent',
        interfaceTheme: message.interfaceTheme || '(not sent)'
    });
    debugChatLog('handleChatSetup body classes:', bodyClasses.join(' ') || '(none)');

    // Add Foundry body classes to DLA's document.body so body.xxx selectors fire
    (message.bodyClasses || []).forEach(cls => {
        if (cls) document.body.classList.add(cls);
    });

    _pendingSetup = {
        styleTexts:    message.styleTexts    || [],
        cssVars:       message.cssVars       || {},
        bodyClasses:   message.bodyClasses   || [],
        interfaceTheme: message.interfaceTheme || '',
        rootFontSize:  message.rootFontSize  || null,
        sidebarWidth:  message.sidebarWidth  || 300,
        dnd5eDiagVars: message.dnd5eDiagVars || {},
    };
}

// ============================================================================
// CHAT INIT — builds the DOM and loads Foundry CSS
// ============================================================================

function applyZoom(container, contentWidth, sidebarWidth) {
    if (contentWidth > 0 && sidebarWidth > 0) {
        const zoom = contentWidth / sidebarWidth;
        container.style.setProperty('--dla-chat-zoom', zoom.toFixed(4));
        debugChatLog(`chat zoom: ${zoom.toFixed(3)} (dla=${Math.round(contentWidth)}px / foundry=${sidebarWidth}px)`);
    }
}

function initChatLog() {
    debugChatLog('initChatLog called');

    const container = document.getElementById('vtt-chat-log');
    if (!container) {
        debugChatLog('initChatLog: ERROR — #vtt-chat-log not found');
        return;
    }

    // Disconnect previous zoom observer before rebuilding DOM
    if (_zoomObserver) {
        _zoomObserver.disconnect();
        _zoomObserver = null;
    }

    const setup              = _pendingSetup || {};
    const styleTexts         = setup.styleTexts         || [];
    const cssVars          = setup.cssVars          || {};
    const bodyClasses      = setup.bodyClasses      || [];
    const interfaceTheme   = setup.interfaceTheme   || '';
    const rootFontSize     = setup.rootFontSize     || null;
    const sidebarWidth       = setup.sidebarWidth       || 300;
    const dnd5eDiagVars      = setup.dnd5eDiagVars      || {};

    // Inject Foundry's embedded CSS blocks into the main document inside a named CSS layer.
    // @layer(foundry) ensures every unlayered DLA rule wins any specificity clash.
    // @import statements cannot appear inside @layer, so they are extracted and
    // converted to layered @import syntax before the layer block.
    // Only injected once — style blocks do not change on reconnect.
    if (!_foundryStylesInjected && styleTexts.length > 0) {
        const layeredImports = [];
        const layerBlocks = [];
        for (const text of styleTexts) {
            const cleaned = text.replace(/^@import\s[^;]+;/gm, match => {
                layeredImports.push(match.replace(/;\s*$/, ' layer(foundry);'));
                return '';
            }).trim();
            if (cleaned) {
                const remapped = cleaned
                    .replace(/:root\b/g, ':where(#dla-sidebar)')
                    .replace(/\bbody\.([\w-]+)/g, ':where(#dla-sidebar).$1');
                layerBlocks.push(remapped);
            }
        }

        // Extract @font-face rules before scoping — @font-face inside @scope is not
        // recognised by Chrome and fonts are never registered. Inject them separately
        // in a plain unscoped <style> so the browser registers them globally.
        const fontFaceRules = [];
        const scopedBlocks = layerBlocks.map(block =>
            block.replace(/@font-face\s*\{[^}]+\}/gi, match => {
                fontFaceRules.push(match);
                return '';
            })
        );
        if (fontFaceRules.length > 0) {
            const fontEl = document.createElement('style');
            fontEl.id = 'foundry-font-faces';
            fontEl.textContent = fontFaceRules.join('\n');
            document.head.appendChild(fontEl);
            debugChatLog(`initChatLog: injected ${fontFaceRules.length} @font-face rules outside @scope`);
        }

        // All blocks go into ONE @scope + @layer so CSS layer ordering
        // (variables < general < specific) applies across all files.
        const cssEl = document.createElement('style');
        cssEl.id = 'foundry-css-layer';
        const allContent = scopedBlocks.join('\n\n');
        cssEl.textContent = [
            ...layeredImports,
            `@scope (#vtt-chat-log) {\n@layer foundry {\n${allContent}\n}\n}`
        ].join('\n\n');
        document.head.appendChild(cssEl);
        _foundryStylesInjected = true;
        debugChatLog(`initChatLog: injected ${styleTexts.length} Foundry style blocks into single scoped layer`);
    }

    // Inject Foundry's runtime CSS vars scoped to #vtt-chat-log.
    // These are the computed values (e.g. dark-theme overrides set by JS),
    // not just stylesheet defaults. Being unlayered they win over layered values.
    // Re-injected on every chatInit in case the theme changed.
    const existingVars = document.getElementById('foundry-css-vars');
    if (existingVars) existingVars.remove();
    if (Object.keys(cssVars).length > 0) {
        const varStyle = document.createElement('style');
        varStyle.id = 'foundry-css-vars';
        const decls = Object.entries(cssVars).map(([k, v]) => `  ${k}: ${v};`).join('\n');
        varStyle.textContent = `#vtt-chat-log #dla-sidebar {\n${decls}\n}`;
        document.head.appendChild(varStyle);
    }

    // Structural layout CSS — injected once.
    // This only covers what is needed for the panel to exist and scroll inside
    // DLA's layout. Nothing inside chat cards is styled here; that is entirely
    // Foundry's responsibility via the loaded stylesheets.
    if (!document.getElementById('foundry-chat-layout')) {
        const layout = document.createElement('style');
        layout.id = 'foundry-chat-layout';
        layout.textContent = `
            #vtt-chat-log {
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            #vtt-chat-log #dla-sidebar {
                position: static;
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                min-height: 0;
            }
            #vtt-chat-log .dla-chat {
                position: static;
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                min-height: 0;
            }
            #vtt-chat-log ol#chat-log {
                position: static;
                flex: 1;
                overflow-y: auto;
                overflow-x: hidden;
                list-style: none;
                margin: 0;
                padding: 4px;
                min-height: 0;
            }
            #vtt-chat-log ol#chat-log > li {
                width: calc(100% - 8px * var(--dla-chat-zoom, 1));
                margin: 0 calc(4px * var(--dla-chat-zoom, 1));
                padding: calc(8px * var(--dla-chat-zoom, 1));
                box-sizing: border-box;
                zoom: var(--dla-chat-zoom, 1);
            }
            #vtt-chat-log ol#chat-log::-webkit-scrollbar { width: 6px; }
            #vtt-chat-log ol#chat-log::-webkit-scrollbar-track { background: transparent; }
            #vtt-chat-log ol#chat-log::-webkit-scrollbar-thumb { background: #9f9275; border-radius: 3px; }
        `;
        document.head.appendChild(layout);
    }

    // Apply Foundry's root font-size to the chat container.
    // This ensures em-based values inside chat cards compute against the same
    // base that Foundry uses, regardless of which game system is active.
    const existingFontSize = document.getElementById('foundry-chat-fontsize');
    if (existingFontSize) existingFontSize.remove();
    if (rootFontSize) {
        const fontSizeStyle = document.createElement('style');
        fontSizeStyle.id = 'foundry-chat-fontsize';
        fontSizeStyle.textContent = `#vtt-chat-log { font-size: ${rootFontSize}; }`;
        document.head.appendChild(fontSizeStyle);
        debugChatLog(`initChatLog: applied rootFontSize=${rootFontSize} to #vtt-chat-log`);
    }

    // Rebuild the chat panel DOM inside #vtt-chat-log
    container.innerHTML = '';

    const sidebar = document.createElement('div');
    sidebar.id = 'dla-sidebar';
    bodyClasses.forEach(cls => { if (cls && !cls.startsWith('theme-')) sidebar.classList.add(cls); });
    sidebar.classList.add('themed', 'theme-light');

    const chatSection = document.createElement('div');
    chatSection.classList.add('dla-chat');

    messageList = document.createElement('ol');
    messageList.id = 'chat-log';

    // Forward clicks on numbered interactive elements to DLC
    messageList.addEventListener('click', e => {
        const dlaTarget = e.target.closest('[data-dla-id]');
        if (!dlaTarget) return;
        const card = e.target.closest('[data-message-id]');
        if (!card) return;
        e.preventDefault();
        e.stopPropagation();
        sendMessage({
            type: 'chatInteraction',
            messageId: card.dataset.messageId,
            dlaId: parseInt(dlaTarget.dataset.dlaId, 10),
            event: 'click'
        });
    });

    // Forward change events (selects, checkboxes) to DLC
    messageList.addEventListener('change', e => {
        const dlaTarget = e.target.closest('[data-dla-id]');
        if (!dlaTarget) return;
        const card = e.target.closest('[data-message-id]');
        if (!card) return;
        e.preventDefault();
        e.stopPropagation();
        const value = (e.target.type === 'checkbox' || e.target.type === 'radio')
            ? e.target.checked
            : e.target.value;
        sendMessage({
            type: 'chatInteraction',
            messageId: card.dataset.messageId,
            dlaId: parseInt(dlaTarget.dataset.dlaId, 10),
            event: 'change',
            value
        });
    });

    chatSection.appendChild(messageList);
    sidebar.appendChild(chatSection);
    container.appendChild(sidebar);

    // Initial zoom: subtract the ol's own padding so chatWidth matches exactly
    // what li { width: 100% } resolves to — avoiding a small but visible error
    // where right-anchored elements (e.g. dice chevron) appear too far right.
    const olStyle = getComputedStyle(messageList);
    const initialWidth = messageList.clientWidth
        - parseFloat(olStyle.paddingLeft  || '0')
        - parseFloat(olStyle.paddingRight || '0');
    applyZoom(container, initialWidth, sidebarWidth);

    // Keep zoom correct whenever the DLA window is resized.
    // ResizeObserver contentRect.width is the content-box width (padding excluded),
    // matching exactly what li { width: 100% } resolves to inside the ol.
    _zoomObserver = new ResizeObserver(entries => {
        for (const entry of entries) {
            applyZoom(container, entry.contentRect.width, sidebarWidth);
        }
    });
    _zoomObserver.observe(messageList);

    const flushed = pendingMessages.length;
    pendingMessages.forEach(msg => handleChatMessage(msg));
    pendingMessages = [];
    debugChatLog('initChatLog: complete', { pendingFlushed: flushed });

}

// ============================================================================
// MESSAGE HANDLERS — called from websocket.js handleMessage
// ============================================================================

function handleChatInit(message) {
    debugChatLog('handleChatInit received');
    initChatLog();
}

// ============================================================================
// STYLE DIFF — compares DLA-rendered card against Foundry reference styles
// ============================================================================

function compareStyles(card, refStyles) {
    const cardId = card.dataset?.messageId || '?';
    let diffs = 0;
    let matches = 0;

    for (const [sel, refList] of Object.entries(refStyles)) {
        const dlaEls = card.querySelectorAll(sel);
        refList.forEach((ref, i) => {
            const el = dlaEls[i];
            if (!el) {
                debugChatLog(`STYLE DIFF [${sel}][${i}]: element missing in DLA`);
                diffs++;
                return;
            }
            const cs = getComputedStyle(el);
            [
                ['color',       ref.color,       cs.color],
                ['bg',          ref.bg,          cs.backgroundColor],
                ['borderStyle', ref.borderStyle, cs.borderStyle],
                ['borderColor', ref.borderColor, cs.borderColor],
                ['position',    ref.position,    cs.position],
            ].forEach(([prop, foundry, dla]) => {
                if (foundry !== dla) {
                    debugChatLog(`STYLE DIFF [${sel}][${i}] ${prop}: foundry=${foundry} dla=${dla}`);
                    diffs++;
                } else {
                    matches++;
                }
            });
            if (ref.before) {
                const bp = getComputedStyle(el, '::before');
                if (ref.before.content !== bp.content)
                    debugChatLog(`STYLE DIFF [${sel}][${i}] ::before content: foundry=${ref.before.content} dla=${bp.content}`);
                if (ref.before.fontFamily !== bp.fontFamily)
                    debugChatLog(`STYLE DIFF [${sel}][${i}] ::before font: foundry="${ref.before.fontFamily.substring(0, 80)}" dla="${bp.fontFamily.substring(0, 80)}"`);
            }
            if (ref.after) {
                const ap = getComputedStyle(el, '::after');
                if (ref.after.content !== ap.content)
                    debugChatLog(`STYLE DIFF [${sel}][${i}] ::after content: foundry=${ref.after.content} dla=${ap.content}`);
                if (ref.after.fontFamily !== ap.fontFamily)
                    debugChatLog(`STYLE DIFF [${sel}][${i}] ::after font: foundry="${ref.after.fontFamily.substring(0, 80)}" dla="${ap.fontFamily.substring(0, 80)}"`);
            }
        });
    }
    debugChatLog(`STYLE DIFF summary id=${cardId}: ${diffs} diffs, ${matches} matches`);
}

function handleChatMessage(message) {
    const id   = message.messageId;
    const html = message.html || '';

    debugChatLog('handleChatMessage received', {
        messageId: id || 'unknown',
        htmlBytes: html.length,
        listReady: !!messageList
    });
    debugChatLog('handleChatMessage HTML preview:', html.substring(0, 4000));

    if (!messageList) {
        pendingMessages.push(message);
        return;
    }

    const template = document.createElement('template');
    template.innerHTML = html;
    const node = template.content.firstElementChild;
    if (!node) return;

    // Strip any <style> or <link> elements inside the card — if left in, they
    // become global CSS when the node is moved to the live document, breaking DLA's UI.
    node.querySelectorAll('style, link[rel="stylesheet"]').forEach(el => el.remove());

    const existing = id
        ? messageList.querySelector('[data-message-id="' + id + '"]')
        : null;

    if (existing) {
        existing.replaceWith(node);
    } else {
        messageList.appendChild(node);
        messageList.scrollTop = messageList.scrollHeight;
    }

}

function handleChatRefStyles(message) {
    const id = message.messageId;
    if (!id || !message.refStyles) return;
    const node = messageList ? messageList.querySelector('[data-message-id="' + id + '"]') : null;
    if (!node) { debugChatLog(`handleChatRefStyles: card ${id} not found in DOM`); return; }
    compareStyles(node, message.refStyles);
}

// ============================================================================
// CHAT TRAY — button wiring (mirrors dice-tray.js accumulation model)
// ============================================================================

let _chatTrayState = { dice: {}, modifier: 0, advMode: 'normal' };

function _buildChatTrayFormula() {
    const { dice, modifier, advMode } = _chatTrayState;
    const parts = [];
    const dieOrder = [20, 12, 10, 8, 6, 4, 100];
    for (const die of dieOrder) {
        const count = dice[die] || 0;
        if (count > 0) {
            let notation = `${count}d${die}`;
            if (die === 20) {
                if (advMode === 'advantage')    notation = `${count}d20kh`;
                else if (advMode === 'disadvantage') notation = `${count}d20kl`;
            }
            parts.push(notation);
        }
    }
    let formula = parts.join('+');
    if (modifier > 0) formula += `+${modifier}`;
    else if (modifier < 0) formula += `${modifier}`;
    return formula;
}

function _rebuildChatInput() {
    const input = document.getElementById('chat-tray-input');
    if (!input) return;
    const formula = _buildChatTrayFormula();
    input.value = formula ? `/roll ${formula}` : '';
}

function _updateChatModifierDisplay() {
    const el = document.getElementById('chat-tray-mod-value');
    if (!el) return;
    const m = _chatTrayState.modifier;
    el.textContent = m > 0 ? `+${m}` : `${m}`;
}

function _updateChatAdvDisButtons() {
    const advBtn = document.getElementById('chat-tray-adv');
    const disBtn = document.getElementById('chat-tray-dis');
    if (advBtn) advBtn.classList.toggle('active', _chatTrayState.advMode === 'advantage');
    if (disBtn) disBtn.classList.toggle('active', _chatTrayState.advMode === 'disadvantage');
}

function _updateChatDieBadge(btn) {
    const die = parseInt(btn.dataset.die);
    const count = _chatTrayState.dice[die] || 0;
    const badge = btn.querySelector('.chat-tray-die-count');
    if (!badge) return;
    badge.textContent = count;
    badge.style.display = count > 0 ? 'block' : 'none';
}

function _resetChatTray() {
    _chatTrayState = { dice: {}, modifier: 0, advMode: 'normal' };
    const input = document.getElementById('chat-tray-input');
    if (input) input.value = '';
    _updateChatModifierDisplay();
    _updateChatAdvDisButtons();
    document.querySelectorAll('.chat-tray-die-btn').forEach(btn => _updateChatDieBadge(btn));
}

function _sendChatMessage() {
    const input = document.getElementById('chat-tray-input');
    if (!input) return;
    const content = input.value.trim();
    if (!content) return;
    sendMessage({ type: 'chatCommand', content });
    _resetChatTray();
}

function initChatTray() {
    // Modifier ± — accumulate, rebuild formula
    const modMinus = document.getElementById('chat-tray-mod-minus');
    const modPlus  = document.getElementById('chat-tray-mod-plus');
    if (modMinus) modMinus.addEventListener('click', () => {
        _chatTrayState.modifier--;
        _updateChatModifierDisplay();
        _rebuildChatInput();
    });
    if (modPlus) modPlus.addEventListener('click', () => {
        _chatTrayState.modifier++;
        _updateChatModifierDisplay();
        _rebuildChatInput();
    });

    // ADV — toggle advantage; clears disadvantage
    const advBtn = document.getElementById('chat-tray-adv');
    if (advBtn) advBtn.addEventListener('click', () => {
        _chatTrayState.advMode = _chatTrayState.advMode === 'advantage' ? 'normal' : 'advantage';
        _updateChatAdvDisButtons();
        _rebuildChatInput();
    });

    // DIS — toggle disadvantage; clears advantage
    const disBtn = document.getElementById('chat-tray-dis');
    if (disBtn) disBtn.addEventListener('click', () => {
        _chatTrayState.advMode = _chatTrayState.advMode === 'disadvantage' ? 'normal' : 'disadvantage';
        _updateChatAdvDisButtons();
        _rebuildChatInput();
    });

    // Visibility buttons — one active at a time
    document.querySelectorAll('.chat-tray-vis-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.chat-tray-vis-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Die buttons — left-click adds, right-click removes; rebuilds formula + badge
    document.querySelectorAll('.chat-tray-die-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const die = parseInt(btn.dataset.die);
            _chatTrayState.dice[die] = (_chatTrayState.dice[die] || 0) + 1;
            _updateChatDieBadge(btn);
            _rebuildChatInput();
        });
        btn.addEventListener('contextmenu', e => {
            e.preventDefault();
            const die = parseInt(btn.dataset.die);
            const current = _chatTrayState.dice[die] || 0;
            if (current > 0) {
                _chatTrayState.dice[die] = current - 1;
                _updateChatDieBadge(btn);
                _rebuildChatInput();
            }
        });
    });

    // Send button + Enter key (Shift+Enter inserts newline)
    const sendBtn = document.getElementById('chat-tray-send');
    const inputEl = document.getElementById('chat-tray-input');
    if (sendBtn) sendBtn.addEventListener('click', _sendChatMessage);
    if (inputEl) {
        inputEl.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                _sendChatMessage();
            }
        });
    }

    debugChatLog('initChatTray: wired up');
}

initChatTray();
