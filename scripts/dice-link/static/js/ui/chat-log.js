/**
 * Chat Log UI Module
 * Renders the Foundry VTT chat log inside a Shadow DOM so Foundry's own
 * stylesheets apply without affecting the rest of the DLA panel.
 */

let shadowRoot = null;
let messageList = null;

/**
 * Initialise the Shadow DOM and inject Foundry's stylesheets.
 * Called when a chatInit message arrives from DLC.
 * @param {string[]} styleUrls - All stylesheet URLs loaded in the Foundry page.
 */
function initChatLog(styleUrls) {
    const container = document.getElementById('vtt-chat-log');
    if (!container) return;

    shadowRoot = container.shadowRoot || container.attachShadow({ mode: 'open' });
    shadowRoot.innerHTML = '';

    // Inject every stylesheet Foundry uses so messages look identical
    for (const url of (styleUrls || [])) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = url;
        shadowRoot.appendChild(link);
    }

    // Layout styles scoped entirely within the shadow
    const style = document.createElement('style');
    style.textContent = `
        :host {
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
        }
        #chat-messages {
            flex: 1;
            overflow-y: auto;
            list-style: none;
            margin: 0;
            padding: 4px 2px;
        }
        #chat-messages::-webkit-scrollbar { width: 6px; }
        #chat-messages::-webkit-scrollbar-track { background: transparent; }
        #chat-messages::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }
    `;
    shadowRoot.appendChild(style);

    messageList = document.createElement('ol');
    messageList.id = 'chat-messages';
    shadowRoot.appendChild(messageList);
}

/**
 * Append a single rendered Foundry chat message to the log.
 * @param {string} html - outerHTML of the Foundry li.chat-message element.
 */
function appendChatMessage(html) {
    if (!messageList) return;
    const template = document.createElement('template');
    template.innerHTML = html;
    const node = template.content.firstElementChild;
    if (node) {
        messageList.appendChild(node);
        messageList.scrollTop = messageList.scrollHeight;
    }
}

/**
 * Handle a chatInit message — set up the shadow panel with Foundry's stylesheets.
 * Exported so websocket.js can call it directly.
 */
function handleChatInit(message) {
    initChatLog(message.styleUrls || []);
}

/**
 * Handle an incoming chat message — append it to the log.
 * Exported so websocket.js can call it directly.
 */
function handleChatMessage(message) {
    if (!shadowRoot) return;
    appendChatMessage(message.html || '');
}
