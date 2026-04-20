# WebRTC SDP Reference for DLA/DLC Communication

## Purpose

WebRTC Data Channels are being used to bypass Private Network Access (PNA) browser security restrictions. WebSockets are blocked by PNA when connecting from an external IP (Vercel-hosted DLC) to localhost (DLA). WebRTC bypasses this restriction.

**Do NOT suggest WebSockets as an alternative.** WebSockets were already tried extensively and do not work without port forwarding due to PNA.

---

## Current Status (April 2026)

**WORKING - Both Firefox and Chrome:**

| Browser | Flow | Status |
|---------|------|--------|
| Firefox | DLA-as-offerer | Working |
| Firefox | Browser-as-offerer | Working |
| Chrome | Browser-as-offerer | Working |
| Chrome | DLA-as-offerer | FAILS (Chrome rejects external offers) |

**Recommendation:** Use **browser-as-offerer** flow for cross-browser compatibility.

---

## The Solution: Browser-as-Offerer Flow

Chrome has strict security validation that rejects externally-generated SDP offers. The solution is to reverse the signaling flow so the browser generates the offer (which Chrome trusts) and DLA generates the answer.

### Why This Works

1. Chrome trusts its own SDP format completely
2. Chrome accepts answers from external sources (DLA) without issue
3. This pattern works in all environments: `file://`, `localhost`, native apps, browser windows

### Implementation Flow

```
DLC (Browser)                           DLA (Python/aiortc)
     |                                       |
     |-- 1. Browser creates offer locally -->|
     |      (RTCPeerConnection.createOffer)  |
     |                                       |
     |-- 2. POST /api/receive-offer -------->|
     |       (send browser's offer to DLA)   |
     |                                       |
     |<-- 3. Answer SDP --------------------|
     |       (DLA generates answer)          |
     |                                       |
     |-- 4. Browser sets remote description  |
     |      (with DLA's answer)              |
     |                                       |
     |<== 5. Data channel opens ============>|
     |<== 6. Bidirectional messages ========>|
```

### DLC Implementation (Browser/JavaScript)

```javascript
// 1. Create peer connection
const pc = new RTCPeerConnection({
    iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }]
});

// 2. Create data channel BEFORE creating offer
const dataChannel = pc.createDataChannel('dice-link');

// 3. Set up data channel handlers
dataChannel.onopen = () => {
    console.log('Data channel opened!');
};

dataChannel.onmessage = (event) => {
    console.log('Message from DLA:', event.data);
};

// 4. Generate offer
const offer = await pc.createOffer();
await pc.setLocalDescription(offer);

// 5. Send offer to DLA
const response = await fetch('http://localhost:8080/api/receive-offer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ offer: pc.localDescription.sdp })
});

const result = await response.json();

// 6. Set DLA's answer as remote description
const answer = new RTCSessionDescription({
    type: 'answer',
    sdp: result.answer
});
await pc.setRemoteDescription(answer);

// 7. Connection established - data channel will open automatically
```

### DLA Implementation (Python/aiortc)

```python
from aiortc import RTCPeerConnection, RTCSessionDescription

# Global reference to store active data channel
active_data_channel = None

async def handle_receive_offer(request):
    """Receive browser's offer and generate answer"""
    global active_data_channel
    
    data = await request.json()
    browser_offer_sdp = data.get("offer")
    
    # Create peer connection
    pc = RTCPeerConnection()
    
    # Handle incoming data channel from browser
    @pc.on("datachannel")
    def on_datachannel(channel):
        global active_data_channel
        active_data_channel = channel
        print(f"Data channel received: {channel.label}")
        
        @channel.on("message")
        def on_message(message):
            print(f"Received from browser: {message}")
        
        @channel.on("close")
        def on_close():
            global active_data_channel
            active_data_channel = None
    
    # Set browser's offer as remote description
    browser_offer = RTCSessionDescription(
        sdp=browser_offer_sdp,
        type="offer"
    )
    await pc.setRemoteDescription(browser_offer)
    
    # Create and set answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    # Return answer to browser
    return web.json_response({
        "answer": pc.localDescription.sdp,
        "status": "success"
    })
```

---

## Critical Lessons Learned

### Lesson 1: Chrome Rejects External Offers

**Chrome has strict security validation for externally-delivered SDP offers.**

When we sent an aiortc-generated offer to Chrome via HTTP, Chrome rejected it with:
```
OperationError: Failed to execute 'setRemoteDescription' on 'RTCPeerConnection': 
Failed to parse SessionDescription. a=candidate:... Invalid SDP line.
```

**Key evidence:**
- The same SDP parsed successfully in Chrome's local diagnostic test
- Firefox accepted the exact same SDP without issues
- Chrome's error was "Invalid SDP line" but the format was correct

**Root cause:** Chrome applies stricter validation to SDPs received from external sources than to locally-generated ones. This is a security feature, not a bug.

**Solution:** Browser-as-offerer flow - Chrome trusts its own offers completely.

### Lesson 2: Line Endings - CRLF Required

**The WebRTC SDP specification (RFC 8866) requires CRLF (`\r\n`) line endings.**

- aiortc generates LF (`\n`) only by default
- Browsers expect and generate CRLF (`\r\n`)
- When constructing SDP in Python, join lines with CRLF:

```python
sdp = "\r\n".join(lines) + "\r\n"
```

### Lesson 3: ICE Candidates MUST Be Included

**The most critical bug we found:** SDP construction code was stripping ICE candidate lines.

Without `a=candidate:` lines, the browser has no connection targets and ICE fails immediately.

**Solution:** Always include all candidates from aiortc's offer:
```python
for line in raw_lines:
    if line.startswith('a=candidate:'):
        candidates.append(line)
```

### Lesson 4: Data Channel Reference Storage

**When DLA creates the data channel (DLA-as-offerer), store reference on `dc.on("open")`:**

```python
dc = pc.createDataChannel("test")

@dc.on("open")
async def on_open():
    global active_data_channel
    active_data_channel = dc  # Store when OUR channel opens
```

**When browser creates the data channel (browser-as-offerer), store reference on `pc.on("datachannel")`:**

```python
@pc.on("datachannel")
def on_datachannel(channel):
    global active_data_channel
    active_data_channel = channel  # Store the received channel
```

### Lesson 5: Firefox vs Chrome Debugging Strategy

1. **Test Firefox first** - Firefox is more lenient, helps verify SDP format is correct
2. **If Firefox works but Chrome fails** - Issue is Chrome-specific validation
3. **Use `about:webrtc` in Firefox** - Shows connection logs, ICE candidates, SDP details
4. **Use Chrome DevTools Console** - Shows specific error messages about SDP parsing

### Lesson 6: IPv4 vs IPv6 Candidates

aiortc auto-discovers all network interfaces including IPv6. Both Firefox and Chrome handle mixed IPv4/IPv6 candidates fine. The real issue was missing candidates entirely, not IPv6 presence.

---

## Working SDP Formats

### Browser-Generated Offer (Chrome)

```
v=0
o=- 3524470939 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=extmap-allow-mixed
a=msid-semantic: WMS
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 0.0.0.0
a=ice-ufrag:xxxx
a=ice-pwd:xxxxxxxxxxxxxxxxxxxx
a=ice-options:trickle
a=fingerprint:sha-256 XX:XX:XX:...
a=setup:actpass
a=mid:0
a=sctp-port:5000
a=max-message-size:262144
```

### DLA-Generated Answer (aiortc)

```
v=0
o=- 3109055570914192449 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=extmap-allow-mixed
a=msid-semantic: WMS
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 0.0.0.0
a=ice-ufrag:xxxx
a=ice-pwd:xxxxxxxxxxxxxxxxxxxx
a=fingerprint:sha-256 XX:XX:XX:...
a=setup:active
a=mid:0
a=sctp-port:5000
a=max-message-size:1073741823
a=candidate:... (IPv4 candidates)
a=candidate:... (IPv6 candidates if present)
```

**Note:** Answerer uses `a=setup:active` (responding to offerer's `actpass`).

---

## API Endpoints for DLA

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/receive-offer` | POST | Receive browser offer, return DLA answer (browser-as-offerer) |
| `/api/offer` | GET | Get DLA offer (DLA-as-offerer, Firefox only) |
| `/api/answer` | POST | Receive browser answer (DLA-as-offerer) |
| `/api/send-message` | POST | Send message to browser via data channel |
| `/api/status` | GET | Check connection status |

**For Chrome compatibility, use `/api/receive-offer` endpoint.**

---

## Common Mistakes (Do NOT Repeat)

1. **Using DLA-as-offerer with Chrome** - Chrome rejects external offers; use browser-as-offerer
2. **Missing ICE candidates** - Offer/answer MUST include `a=candidate:` lines
3. **Wrong line endings** - Use CRLF (`\r\n`), not LF (`\n`)
4. **Wrong data channel reference storage** - Depends on who creates the channel
5. **Assuming Firefox behavior = Chrome behavior** - Always test both
6. **Suggesting WebSockets** - They don't work due to PNA restrictions

---

## Debugging Checklist

### 1. Check Which Flow to Use
- Chrome: Browser-as-offerer only
- Firefox: Either flow works

### 2. Verify Data Channel Created Before Offer
```javascript
// CORRECT: Create channel BEFORE offer
const dc = pc.createDataChannel('test');
const offer = await pc.createOffer();

// WRONG: Creating channel after offer
const offer = await pc.createOffer();
const dc = pc.createDataChannel('test');  // Too late!
```

### 3. Check ICE Candidates Present
```python
for line in sdp.split('\n'):
    if line.startswith('a=candidate:'):
        print(f"Found: {line[:50]}...")
```

### 4. Use Browser Tools
- Firefox: `about:webrtc` for connection logs
- Chrome: DevTools Console for SDP parsing errors

### 5. Verify Line Endings
```python
print(' '.join(f'{ord(c):02x}' for c in sdp[:60]))
# Should see: 0d 0a (CRLF)
```

---

## Test Files

| File | Purpose |
|------|---------|
| `webrtc-test-dla.py` | Python DLA test server with both signaling flows |
| `webrtc-test-dlc.html` | Browser test page with DLA-as-offerer and browser-as-offerer |
| `webrtc-diagnostic.html` | Browser-only diagnostic (two peers in same page) |

---

## Integration Checklist for Main Apps

When integrating WebRTC into the full DLA/DLC apps:

### DLC (Browser/Companion App)

- [ ] Add RTCPeerConnection creation with STUN servers
- [ ] Create data channel before generating offer
- [ ] Implement `createOffer()` and `setLocalDescription()`
- [ ] Send offer to DLA via HTTP POST to `/api/receive-offer`
- [ ] Receive answer and call `setRemoteDescription()`
- [ ] Handle data channel `onopen`, `onmessage`, `onclose` events
- [ ] Implement message protocol for dice rolls, game state, etc.

### DLA (Python Desktop App)

- [ ] Add `/api/receive-offer` endpoint (browser-as-offerer flow)
- [ ] Handle incoming data channel via `pc.on("datachannel")`
- [ ] Store active data channel reference for sending messages
- [ ] Implement message protocol matching DLC
- [ ] Handle connection cleanup on channel close

### Testing

- [ ] Test in Firefox (should work with either flow)
- [ ] Test in Chrome (must use browser-as-offerer)
- [ ] Test bidirectional messaging
- [ ] Test reconnection after disconnect
- [ ] Test in native app environment (Electron or similar)

---

## Version History

- **April 2026 (v3):** Chrome solution found - browser-as-offerer flow works. Full bidirectional messaging verified in both Firefox and Chrome. Document restructured for implementation guidance.
- **April 2026 (v2):** Firefox working with DLA-as-offerer. Documented CRLF requirements, ICE candidate inclusion bug, data channel reference storage.
- **2024 (v1):** Initial documentation from browser diagnostic testing.
