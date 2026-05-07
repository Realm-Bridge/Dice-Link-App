/**
 * Chat Log UI Module
 * Renders the Foundry VTT chat log inside a Shadow DOM so Foundry's own
 * stylesheets apply without affecting the rest of the DLA panel.
 */

let shadowRoot = null;
let messageList = null;
let pendingMessages = [];

/**
 * Initialise the Shadow DOM, inject Foundry's stylesheets, and display messages.
 * @param {string[]} styleUrls  - External stylesheet URLs from Foundry.
 * @param {string[]} styleTexts - Inline stylesheet text content from Foundry.
 * @param {string[]} messages   - outerHTML of existing chat messages to display.
 */
function initChatLog(styleUrls, styleTexts, messages) {
    const container = document.getElementById('vtt-chat-log');
    if (!container) return;

    shadowRoot = container.shadowRoot || container.attachShadow({ mode: 'open' });
    shadowRoot.innerHTML = '';

    // Inject Foundry's external stylesheet(s)
    for (const url of (styleUrls || [])) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = url;
        shadowRoot.appendChild(link);
    }

    // Inject Foundry's inline stylesheets (system and module styles)
    for (const text of (styleTexts || [])) {
        const style = document.createElement('style');
        style.textContent = text;
        shadowRoot.appendChild(style);
    }

    // Layout styles scoped within the shadow
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
            padding: 4px 2px;
            min-height: 0;
        }
        ol.chat-log::-webkit-scrollbar { width: 6px; }
        ol.chat-log::-webkit-scrollbar-track { background: transparent; }
        ol.chat-log::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }
    `;
    shadowRoot.appendChild(layout);

    // Wrapper with .chat-sidebar so ancestor-dependent CSS rules in Foundry apply
    const wrapper = document.createElement('div');
    wrapper.className = 'chat-sidebar flexcol';

    messageList = document.createElement('ol');
    messageList.className = 'chat-log plain themed theme-light';
    wrapper.appendChild(messageList);
    shadowRoot.appendChild(wrapper);

    // Display existing messages bundled in the init payload
    (messages || []).forEach(html => _appendToList(html));

    // Flush any messages that arrived before init completed
    pendingMessages.forEach(html => _appendToList(html));
    pendingMessages = [];
}

/**
 * Append a single rendered message element to the list.
 * @param {string} html - outerHTML of a Foundry li.chat-message element.
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
 * Handle a chatInit message — set up the shadow and display the full history.
 */
function handleChatInit(message) {
    initChatLog(message.styleUrls || [], message.styleTexts || [], message.messages || []);
}

/**
 * Handle a single incoming chat message — append it to the log.
 */
function handleChatMessage(message) {
    if (!messageList) {
        pendingMessages.push(message.html || '');
        return;
    }
    _appendToList(message.html || '');
}
