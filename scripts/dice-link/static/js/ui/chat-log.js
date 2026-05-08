/**
 * Chat Log UI Module
 * Renders incoming Foundry chat messages inside a Shadow DOM.
 * Styling comes from DLA's own chat-cards.css — no Foundry CSS injected.
 */

let shadowRoot = null;
let messageList = null;
let pendingMessages = [];

/**
 * Set up the Shadow DOM with DLA's chat card CSS and an empty message list.
 * Called when a chatInit message arrives from DLC.
 */
function initChatLog() {
    debugChatLog('initChatLog called');

    const container = document.getElementById('vtt-chat-log');
    if (!container) {
        debugChatLog('initChatLog: ERROR — #vtt-chat-log not found');
        return;
    }

    shadowRoot = container.shadowRoot || container.attachShadow({ mode: 'open' });
    shadowRoot.innerHTML = '';

    // DLA's own chat card stylesheet
    const styleLink = document.createElement('link');
    styleLink.rel = 'stylesheet';
    styleLink.href = '/static/css/chat-cards.css';
    shadowRoot.appendChild(styleLink);

    // Layout styles scoped to this Shadow DOM
    const layout = document.createElement('style');
    layout.textContent = `
        :host {
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
        }
        .chat-sidebar {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-height: 0;
        }
        ol.chat-log {
            flex: 1;
            overflow-y: auto;
            list-style: none;
            margin: 0;
            padding: 4px 4px;
            min-height: 0;
        }
        ol.chat-log::-webkit-scrollbar { width: 6px; }
        ol.chat-log::-webkit-scrollbar-track { background: transparent; }
        ol.chat-log::-webkit-scrollbar-thumb { background: #9f9275; border-radius: 3px; }
    `;
    shadowRoot.appendChild(layout);

    const wrapper = document.createElement('div');
    wrapper.className = 'chat-sidebar';

    messageList = document.createElement('ol');
    messageList.className = 'chat-log';
    wrapper.appendChild(messageList);
    shadowRoot.appendChild(wrapper);

    // Flush any messages that arrived before init completed
    const flushed = pendingMessages.length;
    pendingMessages.forEach(html => _appendToList(html));
    pendingMessages = [];
    debugChatLog('initChatLog: complete', { pendingFlushed: flushed });
}

/**
 * Append a single rendered message element to the list.
 */
function _appendToList(html) {
    if (!messageList || !html) return;
    const template = document.createElement('template');
    template.innerHTML = html;
    const node = template.content.firstElementChild;
    if (node) {
        messageList.appendChild(node);
        messageList.scrollTop = messageList.scrollHeight;
    }
}

/**
 * Handle chatInit — set up the Shadow DOM ready to receive messages.
 */
function handleChatInit(message) {
    debugChatLog('handleChatInit received');
    initChatLog();
}

/**
 * Handle a single incoming chat message — append it to the log.
 */
function handleChatMessage(message) {
    debugChatLog('handleChatMessage received', {
        messageId: message.messageId || 'unknown',
        htmlBytes: (message.html || '').length,
        listReady: !!messageList
    });
    if (!messageList) {
        pendingMessages.push(message.html || '');
        return;
    }
    _appendToList(message.html || '');
}
