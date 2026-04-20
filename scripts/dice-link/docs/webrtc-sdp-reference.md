# WebRTC SDP Reference for DLA/DLC Communication

## Purpose

WebRTC Data Channels are being used to bypass Private Network Access (PNA) browser security restrictions. WebSockets are blocked by PNA when connecting from an external IP (Vercel-hosted DLC) to localhost (DLA). WebRTC bypasses this restriction.

**Do NOT suggest WebSockets as an alternative.** WebSockets were already tried extensively and do not work without port forwarding due to PNA.

---

## Current Status (April 2026)

**Working:** Firefox successfully connects to aiortc (Python DLA) with bidirectional data channel messaging.

**Pending:** Chrome testing - Chrome has stricter SDP validation than Firefox and may require additional adjustments.

---

## Critical Lessons Learned

### Lesson 1: Line Endings - CRLF vs LF

**The WebRTC SDP specification (RFC 8866) requires CRLF (`\r\n`) line endings.**

- **Previous documentation was WRONG** - We initially believed browsers wanted LF (`\n`) only
- **Chrome generates CRLF** - When Chrome creates an SDP, it uses `\r\n` line endings
- **aiortc generates LF** - Python's aiortc library generates `\n` only
- **Solution:** When constructing SDP in Python, join lines with `\r\n`:
  ```python
  sdp = "\r\n".join(lines) + "\r\n"
  ```

**How we discovered this:** Hex dump comparison of Chrome-generated SDP vs aiortc-generated SDP revealed `0d0a` (CRLF) vs `0a` (LF) differences.

### Lesson 2: ICE Candidates MUST Be Included in the Offer

**The most critical bug we found:** Our SDP construction code was stripping ICE candidate lines.

- aiortc's `createOffer()` generates an SDP with `a=candidate:` lines containing actual IP addresses and ports
- Our code was extracting various SDP attributes but **never adding the candidates back** to the constructed offer
- Without candidates, the browser has no connection targets and ICE fails immediately

**Firefox Connection Log showed:**
```
Remote component 1 in state 3 - dumping candidates
[NOTHING LISTED]
all checks completed success=0 fail=1
```

**Solution:** Include all `a=candidate:` lines from aiortc's original offer:
```python
# Extract candidates from raw offer
for line in raw_lines:
    if line.startswith('a=candidate:'):
        candidates.append(line)

# Add them to the constructed offer (after SCTP settings)
for candidate in candidates:
    fixed_lines.append(candidate)
```

### Lesson 3: Browser Differences - Firefox vs Chrome

**Firefox is more lenient than Chrome with SDP parsing.**

- Firefox successfully connected once we included ICE candidates
- Chrome rejects externally-delivered SDPs that Firefox accepts
- This is NOT a security bug in Chrome - it's intentional stricter validation
- **Test in Firefox first** to verify SDP format is correct, then address Chrome-specific issues

**Diagnostic approach:** If Firefox works but Chrome doesn't, the issue is Chrome-specific validation, not fundamental SDP format problems.

### Lesson 4: IPv4 vs IPv6 Candidates

**aiortc auto-discovers ALL network interfaces:**
- IPv4 candidates: `192.168.1.55:59010` (local network), `83.105.151.227` (public IP)
- IPv6 candidates: `2a0a:ef40:10cc:7201::...` (if IPv6 is enabled)

**Initial concern:** We thought IPv6 candidates from `file://` origin would fail.

**Actual result:** Firefox handles both IPv4 and IPv6 candidates fine. The real issue was missing candidates entirely, not IPv6 vs IPv4.

**Note:** IPv6 filtering may still be needed for Chrome or other edge cases. The filter logic should check for actual IPv6 address format, not bracket notation (brackets are only used in URLs, not in SDP candidate lines).

### Lesson 5: Data Channel Reference Storage

**When DLA creates the data channel, the `on_datachannel` event does NOT fire on DLA.**

- `on_datachannel` fires when the REMOTE peer creates a channel
- Since DLA is the offerer and creates the channel, DLA must store the reference differently

**Wrong approach:**
```python
@pc.on("datachannel")
async def on_datachannel(channel):
    global active_data_channel
    active_data_channel = channel  # This never fires for DLA!
```

**Correct approach:**
```python
dc = pc.createDataChannel("test")

@dc.on("open")
async def on_open():
    global active_data_channel
    active_data_channel = dc  # Store when OUR channel opens
```

### Lesson 6: Firefox Debugging Tools

**`about:webrtc` in Firefox provides detailed WebRTC diagnostics:**

1. **RTCPeerConnection Statistics** - Shows connection state, ICE stats, raw candidates
2. **Connection Log** - Timestamped events showing exactly what happened
3. **SDP sections** - Shows Local SDP (Answer) and Remote SDP (Offer) as received

**Key things to look for:**
- "Raw Local Candidate" and "Raw Remote Candidate" - should NOT be empty
- ICE State table - shows which candidates succeeded/failed
- Connection Log warnings like "Ignoring loopback addr"

### Lesson 7: The Offer/Answer Flow Matters

**Our flow (DLA as offerer) works with Firefox:**
1. DLA creates offer with data channel
2. Browser receives offer via HTTP fetch
3. Browser creates answer
4. Browser sends answer via HTTP POST
5. DLA sets remote description with browser's answer
6. ICE candidates exchanged
7. Data channel opens

**Alternative flow (browser as offerer) may be needed for Chrome:**
- Some documentation suggests browsers are more lenient when THEY create the offer
- If Chrome continues to reject DLA's offer, we may need to reverse the flow

---

## Working SDP Format (Verified April 2026 - Firefox)

### Offer SDP (from aiortc/DLA)

```
v=0
o=- 3985688943 3985688943 IN IP4 0.0.0.0
s=-
t=0 0
a=group:BUNDLE 0
a=extmap-allow-mixed
a=msid-semantic: WMS
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 0.0.0.0
a=sendrecv
a=ice-pwd:0ed1942bc27f2857310a7678721387f6
a=ice-ufrag:3c477f54
a=mid:0
a=setup:actpass
a=sctp-port:5000
a=max-message-size:1073741823
a=candidate:... (IPv4 and IPv6 candidates from aiortc)
a=candidate:...
a=fingerprint:sha-256 XX:XX:XX:...
```

**Key differences from browser-generated SDP:**
- aiortc uses `0.0.0.0` for origin IP (browsers use `127.0.0.1`)
- aiortc includes `a=sendrecv` (browsers may omit)
- aiortc includes `a=max-message-size` with large value
- Candidates appear after other attributes (order varies)

### Answer SDP (from Firefox)

```
v=0
o=mozilla...THIS_IS_SDPARTA-99.0 5716558636668147076 0 IN IP4 0.0.0.0
s=-
t=0 0
a=sendrecv
a=extmap-allow-mixed
a=fingerprint:sha-256 XX:XX:XX:...
a=ice-options:trickle
a=msid-semantic:WMS *
m=application 0 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 0.0.0.0
a=ice-ufrag:c2b79cfa
a=mid:0
a=setup:active
a=sctp-port:5000
a=max-message-size:1073741823
```

**Note:** Firefox's answer includes `a=setup:active` (responding to offerer's `actpass`).

---

## SDP Construction Requirements

### 1. Line Endings (CRITICAL)

```python
# CORRECT - Use CRLF
sdp = "\r\n".join(lines) + "\r\n"

# WRONG - LF only will fail in some browsers
sdp = "\n".join(lines) + "\n"
```

### 2. Required Attributes (minimum for data channel)

**Session level:**
- `v=0`
- `o=- {session-id} {version} IN IP4 {ip}`
- `s=-`
- `t=0 0`
- `a=group:BUNDLE 0`
- `a=msid-semantic: WMS` or `a=msid-semantic:WMS *`

**Media level:**
- `m=application {port} UDP/DTLS/SCTP webrtc-datachannel`
- `c=IN IP4 0.0.0.0`
- `a=ice-ufrag:{value}`
- `a=ice-pwd:{value}`
- `a=fingerprint:sha-256 {value}`
- `a=setup:{actpass|active}`
- `a=mid:0`
- `a=sctp-port:5000`
- `a=candidate:...` (one or more ICE candidates)

### 3. Setup Values

- **Offerer** uses `a=setup:actpass`
- **Answerer** uses `a=setup:active`

### 4. ICE Candidates

**Format:**
```
a=candidate:{foundation} {component} {protocol} {priority} {ip} {port} typ {type} [other fields]
```

**Example:**
```
a=candidate:0 1 UDP 2122252543 192.168.1.55 59010 typ host
a=candidate:1 1 UDP 1685987327 83.105.151.227 59010 typ srflx raddr 192.168.1.55 rport 59010
```

---

## Common Mistakes (Do NOT Repeat)

1. **Missing ICE candidates** - The offer MUST include `a=candidate:` lines with actual IP addresses
2. **Wrong line endings** - Use CRLF (`\r\n`), not LF (`\n`) only
3. **Storing data channel reference incorrectly** - For the offerer, store on `dc.on("open")`, not `pc.on("datachannel")`
4. **Assuming Firefox behavior = Chrome behavior** - Chrome is stricter; test both
5. **Guessing at SDP format changes** - Always diagnose first with hex dumps and browser tools
6. **Suggesting WebSockets** - They don't work due to PNA restrictions
7. **Stripping candidates during SDP construction** - Always preserve and include ICE candidates

---

## Debugging Checklist

When WebRTC fails:

### 1. Check Line Endings
```python
# Hex dump first 60 bytes
print(' '.join(f'{ord(c):02x}' for c in sdp[:60]))
# Look for: 0d 0a (CRLF) vs 0a (LF)
```

### 2. Verify ICE Candidates Present
```python
# Check offer contains candidates
for line in sdp.split('\n'):
    if line.startswith('a=candidate:'):
        print(f"Found candidate: {line[:50]}...")
```

### 3. Use Firefox about:webrtc
- Open `about:webrtc` in Firefox
- Look at Connection Log for errors
- Check Raw Candidates sections (should NOT be empty)
- Examine ICE State table

### 4. Compare SDPs
- Capture browser-generated SDP (from diagnostic test)
- Compare against aiortc-generated SDP
- Look for missing attributes or format differences

### 5. Check Data Channel State
```javascript
console.log('Data channel state:', dc.readyState);
// Should be: 'connecting' then 'open'
```

---

## Test Files

| File | Purpose |
|------|---------|
| `/scripts/dice-link/tests/webrtc-diagnostic.html` | Browser-only diagnostic (two peers in same page) |
| `/scripts/dice-link/tests/webrtc-test-dla.py` | Python DLA test server with aiortc |
| `/scripts/dice-link/tests/webrtc-test-dlc.html` | Browser DLC test page for connecting to DLA |

---

## Architecture

```
DLC (Browser)                    DLA (Python/aiortc)
     |                                |
     |-- 1. GET /api/offer ---------->|
     |<-- 2. Offer SDP (with ----------|
     |       ICE candidates)          |
     |                                |
     |-- 3. POST /api/answer -------->|
     |       (browser's answer)       |
     |                                |
     |-- 4. POST /api/ice-candidate ->| (browser sends its candidates)
     |                                |
     |<== 5. Data channel opens =====>|
     |<== 6. Bidirectional messages =>|
```

**Note:** ICE candidates flow browser -> DLA. The DLA's candidates are embedded in the offer SDP itself.

---

## Next Steps (Chrome Testing)

1. Test the current working DLA with Chrome instead of Firefox
2. If Chrome rejects the offer, examine the specific error:
   - SDP parsing error? Check format differences
   - ICE failure? Check candidate connectivity
   - Security restriction? May need different approach
3. Consider reversing flow (browser as offerer) if Chrome remains problematic
4. Document Chrome-specific requirements in this file

---

## Version History

- **April 2026 (v2):** Major update after successful Firefox connection. Corrected line ending requirements (CRLF not LF), documented ICE candidate inclusion bug, added Firefox debugging tools, documented data channel reference storage issue.
- **2024 (v1):** Initial documentation from browser diagnostic testing.
