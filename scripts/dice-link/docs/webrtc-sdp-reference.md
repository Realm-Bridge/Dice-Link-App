# WebRTC SDP Reference for DLA/DLC Communication

## Purpose

WebRTC Data Channels are being used to bypass Private Network Access (PNA) browser security restrictions. WebSockets are blocked by PNA when connecting from an external IP (Vercel-hosted DLC) to localhost (DLA). WebRTC may bypass this restriction.

**Do NOT suggest WebSockets as an alternative.** WebSockets were already tried extensively and do not work without port forwarding due to PNA.

---

## Working SDP Format (Verified 2024)

This format was captured from a successful browser-to-browser WebRTC connection diagnostic test.

### Offer SDP (from offerer/initiator)

```
v=0
o=- 4098042193945182461 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=extmap-allow-mixed
a=msid-semantic: WMS
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 0.0.0.0
a=candidate:2261030233 1 udp 2113937151 d1ce6c72-3095-4c5c-b97c-620890bb5e3e.local 61406 typ host generation 0 network-cost 999
a=ice-ufrag:YK/H
a=ice-pwd:hQG2T0r8JtKpW3HsHBWk4TCd
a=ice-options:trickle
a=fingerprint:sha-256 C1:EA:EF:10:50:B7:A5:60:4F:94:75:85:82:DA:9E:F9:6F:66:34:6F:B2:BF:0F:84:62:F7:DC:11:27:F5:B7:E4
a=setup:actpass
a=mid:0
a=sctp-port:5000
a=max-message-size:262144
```

### Answer SDP (from answerer/responder)

```
v=0
o=- 5360767223996646007 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=extmap-allow-mixed
a=msid-semantic: WMS
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 0.0.0.0
a=candidate:3821341452 1 udp 2113937151 d1ce6c72-3095-4c5c-b97c-620890bb5e3e.local 61408 typ host generation 0 network-cost 999
a=ice-ufrag:5q3/
a=ice-pwd:jX/F/1gfK+5XCR1cudNewjCB
a=ice-options:trickle
a=fingerprint:sha-256 6C:1C:F5:D2:DF:9F:54:28:54:08:CF:84:D3:71:71:36:63:86:A1:E2:4D:C1:DB:DD:CA:35:38:58:A0:52:1D:59
a=setup:active
a=mid:0
a=sctp-port:5000
a=max-message-size:262144
```

---

## Critical Requirements

### 1. Line Order Matters

**Session-level (before m= line):**
1. `v=0`
2. `o=- {session-id} 2 IN IP4 127.0.0.1`
3. `s=-`
4. `t=0 0`
5. `a=group:BUNDLE 0`
6. `a=extmap-allow-mixed`
7. `a=msid-semantic: WMS`

**Media-level (after m= line):**
1. `m=application 9 UDP/DTLS/SCTP webrtc-datachannel`
2. `c=IN IP4 0.0.0.0`
3. `a=candidate:...` (all ICE candidates)
4. `a=ice-ufrag:{value}`
5. `a=ice-pwd:{value}`
6. `a=ice-options:trickle`
7. `a=fingerprint:sha-256 {value}`
8. `a=setup:{actpass|active|passive}`
9. `a=mid:0`
10. `a=sctp-port:5000`
11. `a=max-message-size:262144`

### 2. Setup Values

- **Offerer** uses `a=setup:actpass`
- **Answerer** uses `a=setup:active`

### 3. ICE Candidate Exchange is REQUIRED

SDP exchange alone is NOT enough. After setting remote descriptions, ICE candidates MUST be exchanged between peers:

```javascript
// Offerer sends candidates to answerer
offererPc.onicecandidate = (event) => {
    if (event.candidate) {
        answererPc.addIceCandidate(event.candidate);
    }
};

// Answerer sends candidates to offerer
answererPc.onicecandidate = (event) => {
    if (event.candidate) {
        offererPc.addIceCandidate(event.candidate);
    }
};
```

### 4. Line Endings

- Use `\n` (LF) only, NOT `\r\n` (CRLF)
- Remove any `\r` characters from aiortc output

### 5. Fingerprint

- Use only `sha-256` fingerprint
- aiortc may generate multiple (sha-256, sha-384, sha-512) - use only sha-256

---

## Common Mistakes (Do NOT Repeat)

1. **Guessing at SDP format changes** - Always diagnose first, then fix
2. **Missing ICE candidate exchange** - This was the root cause of connection failures
3. **Using aiortc's raw SDP output** - aiortc generates non-standard SDP that browsers reject
4. **Using `\r` line endings** - Browsers expect `\n` only
5. **Wrong setup value in answer** - Answer must use `active`, not `actpass`
6. **Suggesting WebSockets** - They don't work due to PNA restrictions

---

## Test Files

- `/scripts/dice-link/tests/webrtc-diagnostic.html` - Single-page diagnostic that tests browser WebRTC (two peers in same page)
- `/scripts/dice-link/tests/webrtc-test-dla.py` - Python DLA test server
- `/scripts/dice-link/tests/webrtc-test-dlc.html` - Browser DLC test page

---

## Architecture

```
DLC (Browser on Vercel)          DLA (Python on localhost)
         |                                |
         |-- 1. Request offer ----------->|
         |<-- 2. Offer SDP ---------------|
         |                                |
         |-- 3. Answer SDP -------------->|
         |<-- 4. ICE candidates --------->| (bidirectional)
         |                                |
         |<== 5. Data channel open ======>|
         |<== 6. Messages ===============>|
```

---

## Debugging Approach

When WebRTC fails:

1. **Create a diagnostic** - Don't guess, create a minimal test that isolates the problem
2. **Check ICE states** - Log `iceConnectionState` and `connectionState` changes
3. **Verify SDP format** - Compare against the working format in this document
4. **Check ICE candidate exchange** - Candidates must be sent AND received by both peers
5. **Use chrome://webrtc-internals/** - Shows detailed WebRTC debugging info
