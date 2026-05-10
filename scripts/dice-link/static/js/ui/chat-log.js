/**
 * Chat Log UI Module
 * Renders incoming Foundry chat messages inside a Shadow DOM,
 * styled with Foundry's own CSS received via chatSetup.
 */

let shadowRoot = null;
let messageList = null;
let pendingMessages = [];

// CSS setup data received from DLC before chatInit
let _pendingSetup = null;

// ============================================================================
// CHAT SETUP (receives Foundry CSS data from DLC)
// ============================================================================

function handleChatSetup(message) {
    debugChatLog('handleChatSetup received', {
        sheets: (message.styleUrls || []).length,
        vars: Object.keys(message.cssVars || {}).length,
        bodyClasses: (message.bodyClasses || []).length
    });

    // Add Foundry body classes to DLA's page body so body-level CSS selectors fire
    (message.bodyClasses || []).forEach(cls => {
        if (cls) document.body.classList.add(cls);
    });

    // Store for use when chatInit arrives
    _pendingSetup = {
        styleUrls: message.styleUrls || [],
        cssVars: message.cssVars || {}
    };
}

// ============================================================================
// CHAT INIT (builds the Shadow DOM)
// ============================================================================

function initChatLog() {
    debugChatLog('initChatLog called');

    const container = document.getElementById('vtt-chat-log');
    if (!container) {
        debugChatLog('initChatLog: ERROR — #vtt-chat-log not found');
        return;
    }

    shadowRoot = container.shadowRoot || container.attachShadow({ mode: 'open' });
    shadowRoot.innerHTML = '';

    const setup = _pendingSetup || {};
    const styleUrls = setup.styleUrls || [];
    const cssVars = setup.cssVars || {};

    // Inject Foundry's CSS custom properties so colour/size variables resolve inside the shadow tree
    if (Object.keys(cssVars).length > 0) {
        const varStyle = document.createElement('style');
        const decls = Object.entries(cssVars).map(([k, v]) => `  ${k}: ${v};`).join('\n');
        varStyle.textContent = `:host {\n${decls}\n}`;
        shadowRoot.appendChild(varStyle);
    }

    // Font Awesome (always needed, served locally)
    const faLink = document.createElement('link');
    faLink.rel = 'stylesheet';
    faLink.href = '/static/fonts/fontawesome/css/all.min.css';
    shadowRoot.appendChild(faLink);

    // Load all Foundry CSS files via absolute URLs
    styleUrls.forEach(url => {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = url;
        shadowRoot.appendChild(link);
    });

    // Minimal layout styles — only what is needed to position the panel itself
    const layout = document.createElement('style');
    layout.textContent = `
        :host {
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
        }
        #sidebar {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-height: 0;
        }
        section#chat {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-height: 0;
        }
        ol#chat-log {
            flex: 1;
            overflow-y: auto;
            list-style: none;
            margin: 0;
            padding: 4px;
            min-height: 0;
        }
        ol#chat-log::-webkit-scrollbar { width: 6px; }
        ol#chat-log::-webkit-scrollbar-track { background: transparent; }
        ol#chat-log::-webkit-scrollbar-thumb { background: #9f9275; border-radius: 3px; }
    `;
    shadowRoot.appendChild(layout);

    // Build the ancestor structure that Foundry's CSS selectors expect:
    // #sidebar > section#chat > ol#chat-log
    const sidebar = document.createElement('div');
    sidebar.id = 'sidebar';
    sidebar.classList.add(getIsGM() ? 'viewer-gm' : 'viewer-player');

    const chatSection = document.createElement('section');
    chatSection.id = 'chat';

    messageList = document.createElement('ol');
    messageList.id = 'chat-log';

    // Intercept clicks on numbered interactive elements and forward to DLC
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

    // Intercept change events (selects, checkboxes) and forward to DLC
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
    shadowRoot.appendChild(sidebar);

    const flushed = pendingMessages.length;
    pendingMessages.forEach(msg => handleChatMessage(msg));
    pendingMessages = [];
    debugChatLog('initChatLog: complete', { pendingFlushed: flushed });
}

// ============================================================================
// MESSAGE HANDLERS (called from websocket.js handleMessage)
// ============================================================================

function handleChatInit(message) {
    debugChatLog('handleChatInit received');
    initChatLog();
}

/**
 * Handle a single incoming chat message.
 * Replaces existing card in-place by messageId, or appends new card.
 */
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
