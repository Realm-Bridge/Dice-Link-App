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
- **Browser updates lag** - Qt WebEngine updates lag behind Chrome; security patches may come later
- **Login/session persistence** - Cookies and login sessions may not persist between DLA restarts; users may need to log in repeatedly
- **Saved passwords/autofill missing** - Users lose browser convenience features they're used to
- **No browser extensions** - Accessibility tools, screen readers, translators won't work (not critical; workaround: use normal browser for these)
- **File downloads require implementation** - Need to write custom download handler (not difficult but requires code)
- **Audio/video chat in Foundry** - Unknown if this works in embedded Chromium (needs testing)
- **Running Foundry Desktop App** - Embedded browser doesn't help users running Foundry's own Electron app instead of browser

**Assessment of Cons:**
Most cons are **internal and addressable:**
- Session persistence can be implemented
- Download handling is solvable code
- User trust can be built through good design/marketing
- Missing autofill is a minor inconvenience, not a blocker

The challenge of Foundry Desktop App users exists for BOTH approaches (extension doesn't help them either).

**Remaining Questions:**
1. ~~Can Qt WebEngine or CEF properly render Foundry (WebGL, audio, complex UI)?~~ **ANSWERED - See CSS Cascade Layers section below**
2. Will command-line switches work reliably or could they be deprecated?
3. How would Foundry's pop-out windows (v14 feature) interact with embedded browser?
4. Does audio/video chat in Foundry work in embedded Chromium?

---

### CRITICAL FINDING: Foundry v13+ CSS Cascade Layers Incompatibility

**Discovery Date:** April 22, 2026

**The Problem:**
Foundry VTT v13 introduced a complete CSS architecture overhaul using **CSS Cascade Layers** (`@layer` syntax). This is a relatively new CSS feature that requires modern browser support.

**Testing Performed:**
1. Qt WebEngine (PyQt5) loaded Foundry at `http://83.105.151.227:30000/` and `http://localhost:30000/`
2. Page HTML loaded successfully, title displayed "Foundry Virtual Tabletop"
3. **CSS did NOT render** - page appeared completely unstyled (white background, no formatting)
4. Debug revealed: 3 stylesheets loaded, but only 1 CSS rule was accessible
5. Control test: Simple HTML page with standard CSS rendered **perfectly** in Qt WebEngine

**Root Cause - CONFIRMED:**
- **Foundry v13 uses CSS Cascade Layers extensively** with 10+ defined layers:
  - `@layer reset` (lowest priority)
  - `@layer base`
  - `@layer layout`
  - `@layer forms`
  - `@layer foundry`
  - `@layer sheets`
  - `@layer effects`
  - `@layer popovers`
  - `@layer ui`
  - `@layer packages` (highest priority)
  
- **CSS Cascade Layers require Chromium 99+** (released March 2022)
- **PyQt5's Qt WebEngine uses Chromium 83** (released May 2020)
- **Chromium 83 does NOT understand `@layer` syntax** and ignores all layered CSS rules

**Evidence from Foundry Documentation:**
> "The @layer rule is used to create CSS cascade layers. Styles within a given layer can be read by their order in the document (or in the layer declaration) and, unlike un-layered styles, also where they are in layer priority."

> Foundry's layer priority (lowest to highest): reset → base → layout → forms → foundry → sheets → effects → popovers → ui → packages

**Why Control Test Passed:**
Our simple `test-page.html` used standard CSS without `@layer` declarations. Qt WebEngine's Chromium 83 can render standard CSS perfectly - it just cannot parse or apply CSS that uses the `@layer` syntax.

**Implications:**
- **PyQt5 with Qt WebEngine CANNOT render Foundry v13+** - this is a fundamental browser version limitation, not a configuration issue
- No amount of command-line flags can add CSS feature support that doesn't exist in the browser engine
- This is NOT a security issue (same behavior on localhost and external IP)

**CSS Cascade Layers Support Across Foundry Versions:**

**Foundry v13 (current stable - tested on v13.351):**
- From release notes (v13.341): "Community developers can also rejoice as we've migrated entirely to using CSS Layers for Foundry VTT-controlled UI elements"
- Extensive use of CSS Cascade Layers documented
- Requires browser with `@layer` support

**Foundry v14 (latest - v14.360):**
- From release notes: "There are no significant feature changes worth highlighting" (regarding CSS)
- CSS Cascade Layers remain unchanged from v13
- **No new CSS requirements introduced in v14**
- If solution works for v13, it works for v14

**Consequence:** This is not a temporary problem. CSS Cascade Layers are now core to Foundry's architecture and will likely remain so through future versions.

**Next Steps Required:**
1. Determine Chromium version in PyQt6 - does it support CSS Cascade Layers (requires Chromium 99+)?
2. Determine Chromium version in CEF Python - does it support CSS Cascade Layers?
3. If neither supports Chromium 99+, embedded browser approach is NOT viable for any current Foundry version

**Source:** 
- CSS Cascade Layers guide: https://foundryvtt.wiki/en/development/guides/css-cascade-layers
- Foundry v13 release notes (v13.341): https://foundryvtt.com/article/release-13.341
- Foundry v14 release notes (v14.360): https://foundryvtt.com/releases/14.360

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
- **Service worker lifecycle** - Manifest V3 service workers can be terminated by Chrome when idle; need reconnection logic
- **Multiple browser support** - Would need separate extensions for Chrome, Firefox, Edge with different APIs and review processes
- **Extension conflicts** - Other extensions could interfere with ours
- **Corporate/school policies** - Some organizations block extension installation (negligible issue: end users unlikely to use VTT at work/school)
- **Incognito mode** - Extension may be disabled in private browsing mode
- **Review process delays** - Extension store updates require approval; bug fixes slow to reach users
- **Browser update fragility** - Chrome frequently changes extension capabilities; updates could break compatibility
- **Privacy perception** - Extensions often perceived as potential spyware; users may be wary of installing
- **Running Foundry Desktop App** - Extension doesn't work in Foundry's own Electron app either

**Assessment of Cons:**
Most cons are **external dependencies beyond our control:**
- Chrome's Manifest V3 decisions
- Extension store review timelines
- Service worker lifecycle rules
- Multiple browser API differences
- Chrome's deprecation/change decisions

The critical issue: **we depend on Chrome's decisions**, not just our own implementation.

**Similar to embedded browser:** Foundry Desktop App users can't use extensions either.

**Remaining Questions:**
1. Does extension's security context fully bypass Chrome's secure origin requirements?
2. Can content scripts detect clicks on injected links reliably?
3. How maintainable is an extension long-term as Chrome continues changing extension APIs?

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

## Comparative Analysis: Nature of Challenges

### Embedded Browser Cons: Internally Addressable

- Session persistence → Can implement caching/storage
- Download handling → Can write code to handle it
- User trust → Can build through design and marketing
- Missing autofill → Minor convenience, not functional blocker
- Audio/video chat → Can test and potentially solve via configuration

**Key insight:** We control the solution. Challenges are solvable through our own development effort.

### Bridge Extension Cons: External Dependencies

- Manifest V3 decisions → Out of our control
- Extension store review → Out of our control
- Service worker lifecycle → Chrome's design choice
- Multiple browser APIs → Different implementations by different vendors
- Browser update compatibility → Vendors' release cycles

**Key insight:** We depend on other parties' decisions. Challenges could prevent us from delivering if requirements change externally.

---

## Recommendation

**Embedded Browser approach is lower risk** because:
1. Challenges are internally addressable through our own development
2. We have complete control over the Chromium instance and its configuration
3. Security bypass is proven and reliable (command-line switches we control)
4. Simpler long-term maintenance (one rendering engine, one codebase)
5. Better integration with Python ML/vision pipeline

**Bridge Extension carries higher long-term risk** because:
1. Depends on Chrome's continued support for native messaging and extensions
2. Multiple browser support multiplies complexity and maintenance
3. Service worker lifecycle issues could cause reliability problems
4. Extension store review processes can delay critical updates

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
