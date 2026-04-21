# WebRTC Implementation Guide for Dice Link

## Document Purpose

This guide provides step-by-step instructions for implementing WebRTC communication between DLA (Desktop App) and DLC (Browser Companion). Both DLA chat and DLC chat should follow this guide together, completing each checkpoint before moving to the next.

**Required Reading:** Both chats must read `webrtc-sdp-reference.md` before starting. It contains critical lessons from extensive testing.

---

## Why WebRTC? (Context for Both Chats)

### The Problem

Chrome's Private Network Access (PNA) security policy blocks WebSocket connections from HTTP pages to localhost. Since Foundry often runs on HTTP (not HTTPS), WebSocket connections from DLC (browser) to DLA (localhost Python app) are blocked.

This is a browser security policy, not a network issue. It cannot be fixed by port forwarding, CORS headers, or server configuration.

### The Solution

WebRTC bypasses PNA restrictions. After extensive testing, we proved that WebRTC data channels work between an HTTP-served browser page and a localhost Python server.

### Critical Constraint: Browser-as-Offerer

Chrome rejects externally-generated SDP offers as a security measure. The solution is the **browser-as-offerer** pattern:

1. DLC (browser) generates the WebRTC offer locally
2. DLC sends the offer to DLA via HTTP POST
3. DLA generates an answer and returns it
4. DLC sets the answer and connection establishes

This pattern works in both Chrome and Firefox. Do NOT attempt DLA-as-offerer for Chrome compatibility.

### Architecture

```
Same Computer (localhost):
+-------------------------------------------+
|                                           |
|  DLC (Foundry Browser)  <-->  DLA (Python)|
|      localhost:8080                       |
|                                           |
+-------------------------------------------+
```

- All communication is localhost (127.0.0.1)
- No NAT traversal, TURN servers, or port forwarding needed
- 100% connection reliability expected

---

## Implementation Phases

| Phase | Description | DLA Work | DLC Work |
|-------|-------------|----------|----------|
| 1 | Disable WebSocket (keep as fallback) | Yes | Yes |
| 2 | Add WebRTC endpoint to DLA | Yes | No |
| 3 | Add WebRTC client to DLC | No | Yes |
| 4 | Manual integration test | Test | Test |
| 5 | Replace message protocol | Yes | Yes |
| 6 | One-button automated connection | No | Yes |
| 7 | Final integration test | Test | Test |

---

## Phase 1: Disable WebSocket (Keep as Fallback)

### Goal
Disconnect WebSocket code without deleting it, so it remains available as a fallback option.

### DLA Tasks

1. **Locate WebSocket endpoint code** in `server.py`
2. **Comment out or wrap WebSocket routes** with a feature flag
3. **Add a configuration option** in `config.py`:
   ```python
   # Connection method: "webrtc" or "websocket"
   CONNECTION_METHOD = "webrtc"
   ```
4. **Conditionally register WebSocket routes** based on config

### DLC Tasks

1. **Locate WebSocket connection code** in the DLC module
2. **Comment out or wrap WebSocket initialization** with a feature flag
3. **Add equivalent configuration option** for connection method
4. **Ensure WebSocket code can be re-enabled** by changing config

### Checkpoint 1

- [ ] DLA starts without errors with WebSocket disabled
- [ ] DLC loads in Foundry without errors with WebSocket disabled
- [ ] Neither attempts WebSocket connection
- [ ] WebSocket code is preserved and can be re-enabled via config

---

## Phase 2: Add WebRTC Endpoint to DLA

### Goal
Add the `/api/receive-offer` endpoint that accepts browser offers and returns answers.

### DLA Tasks

1. **Add aiortc dependency** if not already present:
   ```
   pip install aiortc
   ```

2. **Create new file** `core/webrtc_handler.py`:
   ```python
   """WebRTC handling for Dice Link - Browser-as-Offerer Pattern"""
   
   from aiortc import RTCPeerConnection, RTCSessionDescription
   from state import app_state
   from debug import log_websocket
   
   # Global peer connection and data channel references
   webrtc_pc = None
   webrtc_data_channel = None
   
   async def handle_receive_offer(offer_sdp: str) -> dict:
       """
       Receive browser's WebRTC offer and generate answer.
       
       This implements the browser-as-offerer pattern required for Chrome.
       See webrtc-sdp-reference.md for why this pattern is necessary.
       """
       global webrtc_pc, webrtc_data_channel
       
       log_websocket("Received WebRTC offer from browser")
       
       # Create new peer connection
       webrtc_pc = RTCPeerConnection()
       
       # Handle incoming data channel from browser
       @webrtc_pc.on("datachannel")
       def on_datachannel(channel):
           global webrtc_data_channel
           webrtc_data_channel = channel
           log_websocket(f"WebRTC data channel received: {channel.label}")
           
           @channel.on("open")
           def on_open():
               log_websocket("WebRTC data channel opened")
               # Update connection state
               app_state.connection.connected = True
           
           @channel.on("message")
           def on_message(message):
               log_websocket(f"WebRTC message received: {message}")
               # Process message - will be expanded in Phase 5
           
           @channel.on("close")
           def on_close():
               global webrtc_data_channel
               webrtc_data_channel = None
               app_state.connection.connected = False
               log_websocket("WebRTC data channel closed")
       
       # Set browser's offer as remote description
       browser_offer = RTCSessionDescription(
           sdp=offer_sdp,
           type="offer"
       )
       
       try:
           await webrtc_pc.setRemoteDescription(browser_offer)
           log_websocket("Browser offer set as remote description")
       except Exception as e:
           log_websocket(f"Error setting remote description: {e}")
           return {"error": str(e), "status": "failed"}
       
       # Create and set answer
       answer = await webrtc_pc.createAnswer()
       await webrtc_pc.setLocalDescription(answer)
       
       answer_sdp = webrtc_pc.localDescription.sdp
       log_websocket(f"Generated answer ({len(answer_sdp)} chars)")
       
       return {
           "answer": answer_sdp,
           "status": "success"
       }
   
   
   async def send_webrtc_message(message: str) -> bool:
       """Send a message through the WebRTC data channel."""
       global webrtc_data_channel
       
       if webrtc_data_channel is None:
           log_websocket("Cannot send: No active WebRTC data channel")
           return False
       
       try:
           webrtc_data_channel.send(message)
           return True
       except Exception as e:
           log_websocket(f"Error sending WebRTC message: {e}")
           return False
   
   
   async def close_webrtc_connection():
       """Close the WebRTC connection and clean up."""
       global webrtc_pc, webrtc_data_channel
       
       if webrtc_pc:
           await webrtc_pc.close()
           webrtc_pc = None
           webrtc_data_channel = None
           app_state.connection.connected = False
           log_websocket("WebRTC connection closed")
   ```

3. **Add route in `server.py`**:
   ```python
   from core.webrtc_handler import handle_receive_offer
   
   @app.post("/api/receive-offer")
   async def receive_offer(request: Request):
       """Receive WebRTC offer from browser (browser-as-offerer pattern)"""
       data = await request.json()
       offer_sdp = data.get("offer")
       
       if not offer_sdp:
           return JSONResponse({"error": "No offer provided"}, status_code=400)
       
       result = await handle_receive_offer(offer_sdp)
       return JSONResponse(result)
   ```

4. **Add CORS headers** for the new endpoint (should already exist from WebSocket setup)

### Checkpoint 2

- [ ] DLA starts without errors
- [ ] `curl -X POST http://localhost:8080/api/receive-offer -H "Content-Type: application/json" -d "{\"offer\": \"test\"}"` returns an error response (expected - invalid SDP)
- [ ] No crashes, endpoint is reachable

---

## Phase 3: Add WebRTC Client to DLC

### Goal
Add WebRTC connection capability to DLC that generates an offer and connects to DLA.

### DLC Tasks

1. **Create WebRTC connection module** (or add to existing connection code):
   ```javascript
   /**
    * WebRTC Connection for Dice Link Companion
    * 
    * Uses browser-as-offerer pattern required for Chrome compatibility.
    * See webrtc-sdp-reference.md for detailed explanation.
    */
   
   class DiceLinkWebRTC {
       constructor(dlaHost = 'localhost', dlaPort = 8080) {
           this.dlaHost = dlaHost;
           this.dlaPort = dlaPort;
           this.peerConnection = null;
           this.dataChannel = null;
           this.onMessage = null;  // Callback for received messages
           this.onConnectionChange = null;  // Callback for connection state changes
       }
       
       /**
        * Connect to DLA using WebRTC
        * This is the main entry point - call this to establish connection
        */
       async connect() {
           console.log('[DLC] Starting WebRTC connection to DLA...');
           
           // 1. Create peer connection with STUN server
           this.peerConnection = new RTCPeerConnection({
               iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }]
           });
           
           // 2. Create data channel BEFORE creating offer (critical!)
           this.dataChannel = this.peerConnection.createDataChannel('dice-link');
           this._setupDataChannelHandlers();
           
           // 3. Generate offer
           const offer = await this.peerConnection.createOffer();
           await this.peerConnection.setLocalDescription(offer);
           
           console.log('[DLC] Generated offer, sending to DLA...');
           
           // 4. Send offer to DLA and get answer
           const response = await fetch(`http://${this.dlaHost}:${this.dlaPort}/api/receive-offer`, {
               method: 'POST',
               headers: { 'Content-Type': 'application/json' },
               body: JSON.stringify({ offer: this.peerConnection.localDescription.sdp })
           });
           
           const result = await response.json();
           
           if (result.error) {
               throw new Error(`DLA rejected offer: ${result.error}`);
           }
           
           console.log('[DLC] Received answer from DLA, setting remote description...');
           
           // 5. Set DLA's answer as remote description
           const answer = new RTCSessionDescription({
               type: 'answer',
               sdp: result.answer
           });
           await this.peerConnection.setRemoteDescription(answer);
           
           console.log('[DLC] Remote description set, waiting for data channel to open...');
           
           // Connection will complete when data channel opens
           // (handled in _setupDataChannelHandlers)
       }
       
       /**
        * Set up handlers for the data channel
        */
       _setupDataChannelHandlers() {
           this.dataChannel.onopen = () => {
               console.log('[DLC] WebRTC data channel opened - connected to DLA!');
               if (this.onConnectionChange) {
                   this.onConnectionChange(true);
               }
           };
           
           this.dataChannel.onclose = () => {
               console.log('[DLC] WebRTC data channel closed');
               if (this.onConnectionChange) {
                   this.onConnectionChange(false);
               }
           };
           
           this.dataChannel.onmessage = (event) => {
               console.log('[DLC] Message from DLA:', event.data);
               if (this.onMessage) {
                   this.onMessage(event.data);
               }
           };
           
           this.dataChannel.onerror = (error) => {
               console.error('[DLC] Data channel error:', error);
           };
       }
       
       /**
        * Send a message to DLA
        */
       send(message) {
           if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
               console.error('[DLC] Cannot send: data channel not open');
               return false;
           }
           
           this.dataChannel.send(message);
           return true;
       }
       
       /**
        * Check if connected
        */
       isConnected() {
           return this.dataChannel && this.dataChannel.readyState === 'open';
       }
       
       /**
        * Disconnect from DLA
        */
       disconnect() {
           if (this.dataChannel) {
               this.dataChannel.close();
           }
           if (this.peerConnection) {
               this.peerConnection.close();
           }
           this.dataChannel = null;
           this.peerConnection = null;
           console.log('[DLC] Disconnected from DLA');
       }
   }
   ```

2. **Integrate with existing DLC connection UI** (if exists) or create simple test button

### Checkpoint 3

- [ ] DLC loads without errors
- [ ] WebRTC code is present but not yet called automatically
- [ ] Manual test: Call `connect()` from browser console, verify no JavaScript errors

---

## Phase 4: Manual Integration Test

### Goal
Verify WebRTC connection works end-to-end with manual testing before automating.

### Test Procedure

1. **Start DLA** on the test computer
2. **Open Foundry with DLC** in browser (Chrome recommended for strictest test)
3. **Open browser DevTools console**
4. **Manually trigger connection**:
   ```javascript
   // Create instance
   const webrtc = new DiceLinkWebRTC('localhost', 8080);
   
   // Set up message handler
   webrtc.onMessage = (msg) => console.log('Received:', msg);
   
   // Connect
   await webrtc.connect();
   ```
5. **Verify in DLA console**: Should see "WebRTC data channel opened"
6. **Test browser to DLA**:
   ```javascript
   webrtc.send('Hello from browser');
   ```
7. **Verify in DLA console**: Should see the message
8. **Test DLA to browser**: Use curl or DLA's send endpoint
   ```bash
   curl -X POST http://localhost:8080/api/send-message -H "Content-Type: application/json" -d "{\"message\": \"Hello from DLA\"}"
   ```
9. **Verify in browser console**: Should see the message

### Checkpoint 4

- [ ] Connection establishes successfully in Chrome
- [ ] Connection establishes successfully in Firefox
- [ ] Browser can send messages to DLA
- [ ] DLA can send messages to browser
- [ ] Connection status is accurately tracked on both sides
- [ ] Disconnect works cleanly

**STOP HERE if any checkpoint fails. Debug before proceeding.**

---

## Phase 5: Replace Message Protocol

### Goal
Replace the WebSocket message protocol with WebRTC-based messaging for dice rolls and game state.

### Understanding the Current Protocol

Both DLA and DLC currently use a JSON message protocol over WebSocket. The same protocol will work over WebRTC data channels - only the transport changes.

Current message types (from existing code):
- `rollRequest` - DLC requests dice roll from user
- `rollResult` - DLA sends dice roll results to DLC
- `diceResult` - DLA sends individual dice results
- `buttonSelect` - User selected Advantage/Normal/Disadvantage
- `diceTrayRoll` - Manual dice roll from UI
- Connection management messages

### DLA Tasks

1. **Route incoming WebRTC messages** to existing handlers:
   ```python
   @channel.on("message")
   def on_message(message):
       # Parse JSON message
       try:
           data = json.loads(message)
           msg_type = data.get("type")
           
           # Route to existing handlers based on message type
           if msg_type == "rollResult":
               # Handle roll result...
           elif msg_type == "buttonSelect":
               # Handle button selection...
           # ... etc
       except json.JSONDecodeError:
           log_websocket(f"Invalid JSON received: {message}")
   ```

2. **Update send functions** to use WebRTC when available:
   ```python
   async def send_to_dlc(message: dict):
       """Send message to DLC via WebRTC or WebSocket (fallback)"""
       message_str = json.dumps(message)
       
       if webrtc_data_channel:
           return await send_webrtc_message(message_str)
       elif websocket_connected:
           return await send_websocket_message(message_str)
       else:
           log_websocket("No connection available to send message")
           return False
   ```

### DLC Tasks

1. **Route incoming WebRTC messages** to existing handlers:
   ```javascript
   webrtc.onMessage = (messageStr) => {
       try {
           const data = JSON.parse(messageStr);
           const msgType = data.type;
           
           // Route to existing handlers
           switch(msgType) {
               case 'rollRequest':
                   handleRollRequest(data);
                   break;
               case 'diceRequest':
                   handleDiceRequest(data);
                   break;
               // ... etc
           }
       } catch (e) {
           console.error('[DLC] Invalid JSON from DLA:', messageStr);
       }
   };
   ```

2. **Update send functions** to use WebRTC:
   ```javascript
   function sendToDLA(message) {
       if (webrtc && webrtc.isConnected()) {
           return webrtc.send(JSON.stringify(message));
       }
       console.error('[DLC] Not connected to DLA');
       return false;
   }
   ```

### Checkpoint 5

- [ ] Existing message types work over WebRTC
- [ ] Dice roll requests flow correctly: DLC -> DLA -> UI -> DLA -> DLC
- [ ] Button selections work
- [ ] Dice tray rolls work
- [ ] No regressions from WebSocket functionality

---

## Phase 6: One-Button Automated Connection

### Goal
User clicks a single button in DLC to initiate and complete the entire WebRTC connection process.

### DLC Tasks

1. **Add "Connect to DLA" button** to DLC UI (if not already present)

2. **Implement connection flow**:
   ```javascript
   async function connectToDLA() {
       // Show connecting state
       updateUI('connecting');
       
       try {
           // Get DLA address from settings (default: localhost:8080)
           const host = game.settings.get('dice-link', 'dlaHost') || 'localhost';
           const port = game.settings.get('dice-link', 'dlaPort') || 8080;
           
           // Create and connect
           window.diceLinkWebRTC = new DiceLinkWebRTC(host, port);
           
           // Set up handlers
           window.diceLinkWebRTC.onMessage = handleDLAMessage;
           window.diceLinkWebRTC.onConnectionChange = (connected) => {
               updateUI(connected ? 'connected' : 'disconnected');
           };
           
           // Connect (this does the full handshake)
           await window.diceLinkWebRTC.connect();
           
           // Success!
           updateUI('connected');
           ui.notifications.info('Connected to Dice Link App');
           
       } catch (error) {
           console.error('[DLC] Connection failed:', error);
           updateUI('disconnected');
           ui.notifications.error(`Failed to connect: ${error.message}`);
       }
   }
   ```

3. **Add disconnect button/functionality**

4. **Add auto-reconnect option** (optional, can be Phase 8)

### Checkpoint 6

- [ ] Single button click initiates connection
- [ ] UI shows connecting/connected/disconnected states
- [ ] Successful connection shows notification
- [ ] Failed connection shows error message
- [ ] Disconnect button works
- [ ] Reconnecting after disconnect works

---

## Phase 7: Final Integration Test

### Goal
Complete end-to-end testing of all functionality.

### Test Scenarios

1. **Fresh connection**
   - [ ] Start DLA
   - [ ] Open Foundry with DLC
   - [ ] Click connect button
   - [ ] Verify connected status

2. **Dice roll flow**
   - [ ] Trigger roll from Foundry (character sheet, macro, etc.)
   - [ ] Verify roll request appears in DLA
   - [ ] Submit dice results in DLA
   - [ ] Verify results appear in Foundry

3. **Manual dice tray**
   - [ ] Use DLA dice tray to roll
   - [ ] Verify results sent to DLC

4. **Connection recovery**
   - [ ] While connected, close DLA
   - [ ] Verify DLC shows disconnected
   - [ ] Restart DLA
   - [ ] Click connect again
   - [ ] Verify reconnection works

5. **Browser compatibility**
   - [ ] Test all above in Chrome
   - [ ] Test all above in Firefox
   - [ ] Test all above in Edge (if supported)

6. **Stress test**
   - [ ] Rapid successive rolls
   - [ ] Multiple button clicks
   - [ ] Long session (30+ minutes)

### Checkpoint 7 (Final)

- [ ] All test scenarios pass
- [ ] No console errors during normal operation
- [ ] Connection is stable over extended use
- [ ] WebSocket fallback code remains intact but disabled
- [ ] Documentation updated with any findings

---

## Troubleshooting Guide

### Connection Fails Immediately

**Symptom:** Error when clicking connect button
**Check:**
1. Is DLA running?
2. Is DLA listening on correct port?
3. Are there CORS errors in browser console?
4. Try: `curl http://localhost:8080/api/receive-offer` - does it respond?

### Connection Establishes But No Messages

**Symptom:** Connected status shown, but messages don't flow
**Check:**
1. Is data channel actually open? (`webrtc.dataChannel.readyState`)
2. Are message handlers registered?
3. Check both DLA and browser console for errors

### Chrome Rejects SDP

**Symptom:** Error about invalid SDP in Chrome
**Check:**
1. Are you using browser-as-offerer pattern?
2. If DLA is generating offer, switch to browser-as-offerer
3. See webrtc-sdp-reference.md "Lesson 1: Chrome Rejects External Offers"

### Works in Firefox, Fails in Chrome

**Symptom:** Everything works in Firefox but Chrome fails
**Check:**
1. Chrome requires browser-as-offerer pattern
2. Check Chrome DevTools console for specific SDP error
3. Verify DLC is generating the offer, not DLA

### Data Channel Never Opens

**Symptom:** Connection seems to establish but `onopen` never fires
**Check:**
1. Was data channel created BEFORE offer? (Critical!)
2. Are ICE candidates being exchanged?
3. Check `about:webrtc` in Firefox for ICE state

---

## Future Enhancements (Not in Initial Implementation)

These are documented for future reference but should NOT be implemented in the initial rollout:

1. **Video streaming** - Add media tracks for camera feed
2. **Auto-reconnect** - Automatic reconnection on disconnect
3. **Connection quality monitoring** - Track latency, packet loss
4. **Multiple peer support** - Connect multiple DLA instances
5. **WebSocket fallback** - Automatic fallback if WebRTC fails

---

## Summary for Quick Reference

### DLA Must:
1. Add `/api/receive-offer` endpoint
2. Accept browser's SDP offer
3. Generate and return SDP answer
4. Handle incoming data channel (browser creates it)
5. Store data channel reference for sending messages

### DLC Must:
1. Create RTCPeerConnection with STUN servers
2. Create data channel BEFORE generating offer
3. Generate offer and send to DLA via HTTP POST
4. Receive answer and set as remote description
5. Handle data channel open/message/close events

### Critical Rules:
- Always use browser-as-offerer pattern (Chrome requirement)
- Create data channel before offer (won't work otherwise)
- Use CRLF line endings in SDP (RFC requirement)
- Include ICE candidates in SDP (connection won't work without them)
- Test in Chrome first (strictest validation)
