# Architecture Decision: Embedded Browser vs Bridge Extension

**Status:** Investigation & Design Phase  
**Last Updated:** April 22, 2026  
**Related Issues:** WebRTC Chrome security restrictions, VTT integration approach

---

## Problem Statement

We need to deliver real physical dice rolls (captured via camera) to VTT canvases (Foundry VTT and eventually Roll20) for all players to see. This serves as proof against cheating concerns - not 3D-rendered dice, but actual video of physical dice rolling.

### Initial Investigation: Why WebRTC Alone Won't Work

Chrome blocks RTCDataChannel and getUserMedia on HTTP origins for security reasons. Chrome's "secure origin" definition is limited to:
- `localhost`, `127.0.0.1`, `::1` (loopback addresses only)
- HTTPS URLs

**Evidence:**
- Test at `http://192.168.1.55` (local network IP) - **FAILED in Chrome**
- Test at `http://83.105.151.227` (external IP) - **FAILED in Chrome**
- Same tests in Firefox - **WORKED**
- Official documentation: https://chromium.org/Home/chromium-security/prefer-secure-origins-for-powerful-new-features

This means GMs hosting Foundry over HTTP (most common) cannot use WebRTC for video streaming if accessed from non-localhost addresses.

---

## Two Architectural Approaches

### Option A: Embedded Browser in DLA

**Concept:** DLA embeds a Chromium-based browser window (Qt WebEngine or CEF Python) that loads the Foundry/Roll20 instance, instead of users accessing the VTT through their normal browser.

**How it bypasses Chrome security:**
- DLA controls the embedded Chromium instance
- Can pass command-line switches: `--unsafely-treat-insecure-origin-as-secure=[URL]`
- Bypasses secure origin restrictions programmatically
- Can programmatically grant camera/microphone permissions

**Architecture:**
```
┌─────────────────────────────────────────────────┐
│                     DLA (Python)                 │
│  ┌──────────────────────┐    ┌───────────────┐  │
│  │  Embedded Browser    │    │  ML/Vision    │  │
│  │  (Qt WebEngine/CEF)  │    │  (OpenCV)     │  │
│  │                      │<-->│               │  │
│  │  Loads Foundry       │    │  - Dice       │  │
│  │  or Roll20           │    │  - Camera     │  │
│  └──────────────────────┘    └───────────────┘  │
└─────────────────────────────────────────────────┘
        ↓ WebSocket ↓
    ┌─────────────────────────┐
    │   DLA Server (Python)   │
    │   - Processes rolls     │
    │   - Manages players     │
    └─────────────────────────┘
```

**Pros:**
- Complete control over browser security settings
- No user setup required (just DLA)
- Clean integration with Python ML/vision code
- Works for both Foundry and Roll20

**Cons:**
- Larger application size (embeds Chromium: ~100-200MB additional)
- Users view VTT through DLA window, not their normal browser
- Need to handle browser UI (navigation, etc.)
- Foundry: Still requires minimal DLC module for player syncing

**Remaining Questions:**
1. Can Qt WebEngine or CEF properly render Foundry (WebGL, audio, complex UI)?
2. Will command-line switches work reliably or could they be deprecated?
3. How would Foundry's pop-out windows (v14 feature) interact with embedded browser?

---

### Option B: Browser Extension Bridge

**Concept:** Users keep using their normal Chrome/Firefox browser. A browser extension acts as a bridge:
- Injects JavaScript into Foundry/Roll20 pages
- Communicates with DLA via native messaging
- Bypasses Chrome security through extension's own security context

**How it bypasses Chrome security:**
- Extension runs in `chrome-extension://` origin (treated as secure)
- Can use native messaging to communicate with local DLA application
- Content scripts can still be limited, but background service workers have more privileges

**Architecture:**
```
┌─────────────────────────────────┐
│     Browser (Chrome/Firefox)    │
│  ┌──────────────────────────┐   │
│  │  Foundry/Roll20 Page     │   │
│  │  ┌────────────────────┐  │   │
│  │  │ Injected Content   │  │   │
│  │  │ Script (watches    │  │   │
│  │  │ chat, requests)    │  │   │
│  │  └────────────────────┘  │   │
│  └──────────────────────────┘   │
│           ↓ Native Messaging ↓   │
│  ┌──────────────────────────┐   │
│  │  Extension Background    │   │
│  │  Service Worker          │   │
│  │  (secure context)        │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
           ↓ WebSocket ↓
    ┌─────────────────────────┐
    │   DLA Server (Python)   │
    │   - Processes rolls     │
    │   - Manages players     │
    └─────────────────────────┘
```

**Pros:**
- Users keep their normal browser experience
- Smaller footprint (just extension code)
- Can leverage browser extensions users already trust
- Potentially easier to maintain than embedded browser

**Cons:**
- Users must install extension
- Extension security context still has limitations (getUserMedia still requires HTTPS in some cases)
- Extension distribution/maintenance overhead
- Need to develop in JavaScript (separate from Python DLA codebase)
- May not fully bypass all Chrome security restrictions

**Remaining Questions:**
1. Does extension's security context fully bypass Chrome's secure origin requirements?
2. Can content scripts detect clicks on injected links reliably?
3. How maintainable is an extension long-term as Chrome updates?

---

## VTT-Specific Requirements

### Foundry VTT

**Current Status:** CONFIRMED NEEDED - Cannot eliminate DLC module entirely

**Why:**
- Foundry syncs dice results via `game.socket.emit()` - requires module registration
- Without a module, injected JS can only affect local user's view
- Other players won't see the dice roll

**What remains possible:**
- Minimal DLC module (only GM-level configuration in Foundry itself)
- All user-facing features in DLA (embedded browser or extension)
- Roll data flows: User camera → DLA → DLC module → Foundry chat → all players

**Applies to both approaches:** Embedded browser and bridge extension both still need minimal DLC module.

### Roll20 VTT

**Current Status:** FALLBACK APPROACH IDENTIFIED

**Challenge:**
- Roll20 is more restrictive ("walled garden")
- No equivalent to Foundry's socket system for custom modules
- No API access for free/Plus GMs (Pro subscription required)

**Fallback Solution (both approaches can use):**
1. Player rolls dice → video saved in DLA with unique ID
2. Result posted to Roll20 chat via injected JS: "Mike rolled 2d6: 7 [Verify: #12345]"
3. GM clicks "Verify" → triggers request message
4. DLA sees request in chat, uploads video to cloud service
5. DLA posts cloud link back to chat (whispered to GM only)
6. GM views video proof at leisure

**Confirmed feasible without API:**
- Injecting text into chat input: `/w gm [message]` format (whisper syntax)
- Chat whispers are visible only to specified player
- Base64-encoded file URLs work in browsers (though video size TBD)

**Still needs testing:**
- Can we inject clickable links that remain intact in Roll20 chat?
- Can we detect when link is clicked?
- Does Roll20 sanitize/remove embedded links?

**Important:** These Roll20 questions apply equally to BOTH approaches. They're not blocking factors for choosing between embedded browser vs bridge - they're deferred until Roll20 support is actually built.

---

## Decision Matrix

| Factor | Embedded Browser | Bridge Extension |
|--------|------------------|------------------|
| Chrome security bypass | ✓ Complete control | ⚠️ Partial (may still need testing) |
| User setup required | ✗ None | ✓ Install extension |
| VTT integration - Foundry | ✓ Works (minimal DLC) | ✓ Works (minimal DLC) |
| VTT integration - Roll20 | ⚠️ Needs testing | ⚠️ Needs testing |
| Application size | ✗ Large (+100-200MB) | ✓ Small |
| User experience | ⚠️ Custom browser | ✓ Normal browser |
| Python integration | ✓ Native (same process) | ⚠️ Via native messaging |
| Development complexity | ⚠️ Medium (build UI) | ⚠️ Medium (extension APIs) |
| Long-term maintenance | ⚠️ Chromium updates | ⚠️ Chrome extension changes |

---

## Next Steps

### Phase 1: Foundry Support (Current)

**Decision needed:** Embedded Browser vs Bridge Extension
- Both support Foundry with minimal DLC module
- Choice should be based on user experience preference, development effort, and application size constraints
- Roll20 questions don't affect this decision

### Phase 2: Roll20 Support (Future)

**Deferred questions:**
- Can we inject clickable links that work in Roll20 chat?
- Can we detect clicks on those links?
- What's the cloud service strategy for video hosting?

### Phase 3: Testing & Refinement

Once approach is chosen:
- Test with actual Foundry instances
- Test with actual Roll20 instances
- Measure performance impact
- Verify video quality/file sizes

---

## References

- Chromium Secure Origins: https://chromium.org/Home/chromium-security/prefer-secure-origins-for-powerful-new-features
- Qt WebEngine docs: https://doc.qt.io/qt-6/qwebengine-index.html
- CEF Python docs: https://github.com/cztomczak/cefpython
- Chrome Extension native messaging: https://developer.chrome.com/docs/extensions/mv3/messaging/
- Beyond20 extension (reference): https://github.com/kakaroto/Beyond20

---

## Open Questions for DLC Chat

1. What is the preference for user experience: custom DLA window or keeping normal browser?
2. What are the constraints on application size for DLA?
3. Should we prioritize Foundry-only launch, or design for Roll20 from the start?
