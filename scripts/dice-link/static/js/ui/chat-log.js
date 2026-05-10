/**
 * Chat Log UI Module
 * Renders incoming Foundry chat messages inside the control panel,
 * styled with Foundry's own CSS loaded into the main document via @layer.
 *
 * CSS loading strategy:
 *   - Foundry stylesheet URLs are imported as @layer(foundry) so DLA's own
 *     (unlayered) CSS always wins any specificity clash.
 *   - DLA's document.body already carries Foundry's body classes (added in
 *     handleChatSetup), so body.xxx selectors in Foundry's CSS fire correctly.
 *   - Computed CSS vars received from DLC are scoped to #vtt-chat-log and are
 *     unlayered, so they override any layered stylesheet defaults.
 *   - Layout and image-constraint overrides are scoped to #vtt-chat-log so
 *     they cannot affect the rest of DLA's UI.
 */

let messageList = null;
let pendingMessages = [];
let _foundryStylesInjected = false;
let _pendingSetup = null;

// ============================================================================
// CHAT SETUP — receives Foundry CSS data from DLC before chatInit
// ============================================================================

function handleChatSetup(message) {
    debugChatLog('handleChatSetup received', {
        sheets: (message.styleUrls || []).length,
        vars: Object.keys(message.cssVars || {}).length,
        bodyClasses: (message.bodyClasses || []).length
    });

    // Add Foundry body classes to DLA's document.body so body.xxx CSS selectors fire
    (message.bodyClasses || []).forEach(cls => {
        if (cls) document.body.classList.add(cls);
    });

    _pendingSetup = {
        styleUrls: message.styleUrls || [],
        cssVars: message.cssVars || {},
        bodyClasses: message.bodyClasses || []
    };
}

// ============================================================================
// CHAT INIT — builds the DOM and loads Foundry CSS
// ============================================================================

function initChatLog() {
    debugChatLog('initChatLog called');

    const container = document.getElementById('vtt-chat-log');
    if (!container) {
        debugChatLog('initChatLog: ERROR — #vtt-chat-log not found');
        return;
    }

    const setup = _pendingSetup || {};
    const styleUrls = setup.styleUrls || [];
    const cssVars = setup.cssVars || {};
    const bodyClasses = setup.bodyClasses || [];

    // Load all Foundry stylesheets into the main document inside a named CSS layer.
    // @layer(foundry) means every unlayered DLA rule automatically wins on conflicts —
    // Foundry's global rules (button, img, body, etc.) cannot override DLA's own styling.
    // Only done once per session; Foundry stylesheet URLs don't change on reconnect.
    if (!_foundryStylesInjected && styleUrls.length > 0) {
        const importStyle = document.createElement('style');
        importStyle.id = 'foundry-css-layer';
        importStyle.textContent = styleUrls
            .map(url => `@import url("${url}") layer(foundry);`)
            .join('\n');
        document.head.appendChild(importStyle);
        _foundryStylesInjected = true;
        debugChatLog(`initChatLog: injected ${styleUrls.length} Foundry stylesheets as layer(foundry)`);
    }

    // Inject Foundry's computed CSS vars scoped to #vtt-chat-log.
    // These are the runtime-resolved values (e.g. dark theme values set by JS),
    // not just the stylesheet defaults. Being unlayered, they win over layered values.
    const existingVars = document.getElementById('foundry-css-vars');
    if (existingVars) existingVars.remove();
    if (Object.keys(cssVars).length > 0) {
        const varStyle = document.createElement('style');
        varStyle.id = 'foundry-css-vars';
        const decls = Object.entries(cssVars).map(([k, v]) => `  ${k}: ${v};`).join('\n');
        varStyle.textContent = `#vtt-chat-log {\n${decls}\n}`;
        document.head.appendChild(varStyle);
    }

    // Layout and image constraints scoped to #vtt-chat-log.
    // Injected once — does not change on reconnect.
    if (!document.getElementById('foundry-chat-layout')) {
        const layout = document.createElement('style');
        layout.id = 'foundry-chat-layout';
        layout.textContent = `
            #vtt-chat-log {
                display: flex;
                flex-direction: column;
                height: 100%;
                overflow: hidden;
            }
            #vtt-chat-log #sidebar {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                min-height: 0;
            }
            #vtt-chat-log section#chat {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                min-height: 0;
            }
            #vtt-chat-log ol#chat-log {
                flex: 1;
                overflow-y: auto;
                list-style: none;
                margin: 0;
                padding: 4px;
                min-height: 0;
            }
            #vtt-chat-log ol#chat-log::-webkit-scrollbar { width: 6px; }
            #vtt-chat-log ol#chat-log::-webkit-scrollbar-track { background: transparent; }
            #vtt-chat-log ol#chat-log::-webkit-scrollbar-thumb { background: #9f9275; border-radius: 3px; }
            #vtt-chat-log img {
                max-width: 100%;
                height: auto;
            }
            #vtt-chat-log .message-header img,
            #vtt-chat-log .profile-image,
            #vtt-chat-log img.profile-image,
            #vtt-chat-log .author-avatar img {
                width: 36px;
                height: 36px;
                object-fit: cover;
                border-radius: 50%;
            }
        `;
        document.head.appendChild(layout);
    }

    // Rebuild the chat panel DOM inside #vtt-chat-log
    container.innerHTML = '';

    const sidebar = document.createElement('div');
    sidebar.id = 'sidebar';
    // Mirror Foundry's body classes onto #sidebar so CSS rules that use those classes
    // as ancestors (e.g. .dnd5e-theme-dark .chat-message) fire correctly inside the panel
    bodyClasses.forEach(cls => { if (cls) sidebar.classList.add(cls); });

    const chatSection = document.createElement('section');
    chatSection.id = 'chat';

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

function handleChatMessage(message) {
    const id = message.messageId;
    const html = message.html || '';

    debugChatLog('handleChatMessage received', {
        messageId: id || 'unknown',
        htmlBytes: html.length,
        listReady: !!messageList
    });

    if (!messageList) {
        pendingMessages.push(message);
        return;
    }

    const template = document.createElement('template');
    template.innerHTML = html;
    const node = template.content.firstElementChild;
    if (!node) return;

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
