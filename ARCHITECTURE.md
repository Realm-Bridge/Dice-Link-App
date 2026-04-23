# Dice Link — Architecture Overview

**Version 3.0 | April 23, 2026**  
**Realm Bridge Ltd. | Confidential**

---

## What This Document Covers

This document describes the revised technical architecture for the Dice Link desktop application based on discoveries from initial prototype development. It covers the chosen tech stack, project structure, environment variables, data models, and critical integration patterns.

For product scope and user flows, refer to the Full Vision Specification.

**Note:** This is a major revision from Version 2.0. See `ARCHITECTURE-OLD.md` for the original plan and `scripts/dice-link/docs/architecture-decision-embedded-vs-bridge.md` for the detailed technical rationale behind the changes.

---

## Key Architectural Change: Embedded Browser Integration

### Original Approach (v2.0)
- Users access VTTs (Foundry, Roll20, etc.) in their normal browsers
- DLA connects externally via WebSocket to communicate with VTT plugins/extensions
- Separate windows: VTT in browser, DLA controls in PyWebView app

### New Approach (v3.0)
- **DLA embeds VTTs directly** inside PyQt6 QWebEngineView containers
- Communication with VTTs is **internal JavaScript injection**, not external WebSocket
- Dual independent windows: Foundry browser (fullscreen-capable), DLA controls (separate window)
- VTTs are viewed and interacted with inside DLA, not in the user's normal browser

**Why this change:**
Chromium browsers block WebRTC/getUserMedia on HTTP origins for security reasons. Most GMs host Foundry over HTTP. The embedded browser approach uses Qt command-line flags to bypass these restrictions safely while running on the user's machine.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Desktop app shell** | **PyQt6 + QWebEngineView** (revised) | Cross-platform; provides full browser control: popup interception, JS injection, window management |
| App backend | Python + Flask | Unchanged: handles camera, inference, database, uploads |
| App frontend | Vanilla JavaScript | Unchanged: DLA controls UI |
| Frontend UI framework | Custom CSS + Semantic HTML | Unchanged |
| **VTT display (Foundry)** | **PyQt6 QWebEngineView** (new) | Embeds Foundry VTT directly; allows JS injection for dice interception |
| **VTT module (Foundry)** | **JavaScript (minimal)** (revised) | Still required but role simplified: relays roll results to other players. No longer needs WebSocket client code. |
| ML training | Python + PyTorch + YOLO v11 | Unchanged |
| ML inference | ONNX Runtime (Python) | Unchanged |
| Camera access | OpenCV (Python) | Unchanged |
| Local storage | JSON files (MVP) → SQLite (v1.1+) | Unchanged |
| Cloud storage | AWS S3 | Unchanged |
| Cloud API | AWS Lambda + API Gateway | Unchanged: error packages, model updates, dice set sync |
| **Browser extensions** | **JavaScript (future)** (revised) | For other VTTs (Roll20, etc.). Approach TBD but likely similar embedded browser pattern or traditional WebSocket if VTT supports it |

---

## System Architecture

### Dual Window System

**DLA Controls Window (QMainWindow)**
- Dice controls, formula bar
- Camera preview / selection
- Settings panel
- Connection status to VTT
- Model version display

**VTT Browser Window (QMainWindow)**
- Embedded VTT (Foundry VTT for v1.0)
- Displays to user in fullscreen (optional, on separate monitor)
- Can be minimized/moved independently

Both windows run in the same Qt application process but are separate top-level windows that communicate via:
- Qt signals/slots
- Shared Python state
- JavaScript injection

```
┌──────────────────────────────────────────┐
│        DLA Controls Window (Qt)           │
│  ┌─────────────────────────────────────┐ │
│  │  Dice Controls                      │ │
│  │  Camera Selection                   │ │
│  │  Settings                           │ │
│  │  Status                             │ │
│  └─────────────────────────────────────┘ │
│              │                            │
│              │ Qt signals / shared state  │
│              ▼                            │
│  Foundry Module (injected JS)            │
│  Intercepts dice rolls                   │
│  Sends to DLA backend                    │
└──────────────────────────────────────────┘
              │
              │ (same process, different window)
              ▼
┌──────────────────────────────────────────┐
│    VTT Browser Window (Qt)                │
│  ┌─────────────────────────────────────┐ │
│  │  Foundry VTT                        │ │
│  │  (full Foundry interface)           │ │
│  │                                     │ │
│  │  Popouts work properly              │ │
│  │  (with location.hash patch)         │ │
│  └─────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

---

## Project Structure

```
dice-link/
├── app/                          # Desktop application
│   ├── app.py                    # Main entry point (creates Qt app + dual windows)
│   ├── config.py                 # Configuration
│   ├── requirements.txt           # Python dependencies
│   ├── windows/
│   │   ├── __init__.py
│   │   ├── controls.py           # DLA Controls window (QMainWindow)
│   │   ├── foundry_browser.py    # VTT Browser window (QMainWindow)
│   │   └── popout.py             # PopOut window handler
│   ├── static/
│   │   ├── js/
│   │   │   ├── client.js         # WebSocket client for Flask backend
│   │   │   ├── state.js          # State management
│   │   │   ├── utils.js          # Utilities
│   │   │   └── ui/
│   │   │       ├── controls.js   # Dice controls UI
│   │   │       ├── settings.js   # Settings UI
│   │   │       └── status.js     # Status UI
│   │   ├── css/
│   │   │   └── style.css
│   │   └── DLC Dice/             # SVG assets
│   ├── core/
│   │   ├── camera.py             # Camera access (OpenCV)
│   │   ├── inference.py          # ONNX inference
│   │   ├── vtt_integration.py    # VTT-specific logic
│   │   ├── js_injection.py       # JavaScript injection helpers
│   │   └── storage.py            # Database operations
│   ├── js_patches/               # JavaScript patches for VTTs
│   │   ├── foundry_v13.js        # Foundry v13 patches
│   │   ├── foundry_v14.js        # Foundry v14 patches (when available)
│   │   └── popout_patch.js       # Universal popout handler
│   └── scripts/
│       └── build_exe.py          # PyInstaller config
├── ml/                           # ML training (unchanged)
├── server/                       # AWS Lambda (unchanged)
├── foundry-module/               # Foundry VTT module (SIMPLIFIED)
│   ├── src/
│   │   ├── module.js             # Entry point - relays rolls to other players
│   │   └── hooks.js              # Hook definitions (dice roll interception)
│   ├── lang/
│   └── module.json
├── ARCHITECTURE-OLD.md           # Previous architecture (for reference)
└── README.md
```

---

## Communication Flow: Foundry Dice Rolls

### Step 1: User rolls dice in Foundry
Foundry creates a roll event in the chat.

### Step 2: Injected Foundry Module intercepts
```javascript
// Injected into Foundry page by DLA at startup
Hooks.on('renderChatMessage', (app, html, data) => {
  // Find dice rolls in the chat
  // Call back to DLA backend
});
```

### Step 3: JavaScript calls Python backend
```python
# In DLA backend (Flask)
@app.route('/api/foundry/roll', methods=['POST'])
def handle_foundry_roll():
    # Roll data arrives here
    # Perform inference on camera frame
    # Return updated roll values
```

### Step 4: DLA injects response back into Foundry
If the user corrects the roll, DLA injects JavaScript to update Foundry's roll object in real-time.

### Step 5: Foundry Module broadcasts to other players
The Foundry module uses `game.socket.emit()` to send the final roll to all connected players:
```javascript
game.socket.emit('module.dice-link', {
  type: 'rollResult',
  data: correctedRoll
});
```

---

## Critical Integration Details

### Qt WebEngine Chromium Flags (MANDATORY)

To allow HTTP origins to use WebRTC, getUserMedia, and other "powerful features", pass these flags to `QApplication()` via `sys.argv`:

```python
import sys
from urllib.parse import urlparse

FOUNDRY_URL = "http://gm-machine.local:30000"  # Example
parsed = urlparse(FOUNDRY_URL)
origin = f"{parsed.scheme}://{parsed.netloc}"

QT_ARGS = [sys.argv[0]]
QT_ARGS.extend([
    f'--unsafely-treat-insecure-origin-as-secure={origin}',
    '--disable-web-security',
    '--disable-features=CrossOriginOpenerPolicy',
    '--disable-features=CrossOriginEmbedderPolicy',
    '--allow-running-insecure-content',
    '--disable-site-isolation-trials',
    '--disable-features=IsolateOrigins',
    '--disable-features=site-per-process',
    '--test-type',
    '--ignore-certificate-errors',
])

from PyQt6.QtWidgets import QApplication
app = QApplication(QT_ARGS)
```

**Important:** Pass to `QApplication()`, NOT as environment variables. `QTWEBENGINE_CHROMIUM_FLAGS` does not work reliably.

Reference: `scripts/dice-link/tests/pyqt6-test2-secure-origin.py`

### Foundry PopOut Module Handling (CRITICAL)

Foundry's PopOut module fails in Qt WebEngine because popup windows lack a `.location` property. Solution:

**1. Patch `window.open()` at startup:**
```javascript
// Installed before Foundry module loads
var originalWindowOpen = window.open;
window.open = function(url, name, features) {
    var popup = originalWindowOpen.call(window, url, name, features);
    if (!popup) return null;
    
    // Add missing .location property
    if (!popup.location) {
        popup.location = { hash: "", href: url || "about:blank" };
    }
    return popup;
};
```

**2. Intercept OS close button in PopupWindow:**
When user clicks OS close button (red X), instead of closing immediately:
- Use JavaScript to click the sheet's close button (Foundry's button)
- This triggers PopOut's unload handler which returns sheet data to main window
- After delay (~300-500ms), allow Qt window to close

This prevents sheet data loss.

Reference: `scripts/dice-link/docs/architecture-decision-embedded-vs-bridge.md` - PopOut Module section

### Navigation Control

The embedded VTT browser must prevent users from navigating away from the VTT:

```python
def acceptNavigationRequest(self, url, navigation_type, isMainFrame):
    # Only allow navigation within the VTT domain
    allowed_domain = urlparse(self.FOUNDRY_URL).netloc
    requested_domain = urlparse(url.toString()).netloc
    
    return requested_domain == allowed_domain
```

---

## Environment Variables

### Desktop App (`app/`)

| Variable | Purpose |
|---|---|
| `DICE_LINK_ENV` | `development` or `production` |
| `DICE_LINK_API_BASE_URL` | AWS API Gateway URL |
| `DICE_LINK_API_KEY` | AWS authentication key |
| `DICE_LINK_APPDATA_PATH` | User data storage (set at runtime) |
| `FOUNDRY_URL` | URL of target Foundry instance (e.g., `http://localhost:30000`) |
| `FOUNDRY_ADMIN_KEY` | Admin key for Foundry API calls (if needed) |

### AWS Lambda (`server/`)

| Variable | Purpose |
|---|---|
| `AWS_REGION` | AWS region |
| `S3_BUCKET_MODELS` | ONNX model storage |
| `S3_BUCKET_ERROR_PACKAGES` | Error packages (for training data collection) |
| `S3_BUCKET_DICE_SETS` | Personal dice set sync |
| `MODEL_MANIFEST_KEY` | Version manifest path in S3 |

### ML Training (`ml/`)

| Variable | Purpose |
|---|---|
| `TRAINING_DATA_PATH` | Annotated training images location |
| `MODEL_OUTPUT_PATH` | Exported ONNX model location |
| `YOLO_EPOCHS` | Training runs |
| `YOLO_CONFIDENCE_THRESHOLD` | Minimum confidence for valid results |

---

## Data Models

Same as ARCHITECTURE-OLD.md (unchanged):
- `RollResult`
- `ErrorPackage`
- `Session`
- `AppSettings`
- `PersonalDiceSet`
- `DieProfile`
- `TrainingImage`

See ARCHITECTURE-OLD.md for full schema definitions.

---

## Foundry Module Role (SIMPLIFIED)

The Foundry VTT module is STILL REQUIRED but its role is simplified:

**Old role (v2.0):**
- WebSocket client connecting to DLA's local server
- Receives roll results from WebSocket
- Broadcasts to other players via `game.socket.emit()`

**New role (v3.0):**
- DLA injects JavaScript directly (no WebSocket needed for Foundry)
- Module acts as "receiver" of injected messages
- Still broadcasts to other players via `game.socket.emit()`
- Minimal code needed: mostly just hook definitions and socket broadcasting

```javascript
// Simplified module.js
Hooks.once('init', () => {
  // Listen for injected messages from DLA
  window.addEventListener('diceLinkRollResult', (event) => {
    const rollData = event.detail;
    game.socket.emit('module.dice-link', {
      type: 'rollResult',
      data: rollData
    });
  });
});
```

---

## Testing Strategy

All critical integration points have been tested:

- [x] PyQt6 WebEngine loading HTTP origins
- [x] Chromium flags allowing WebRTC/getUserMedia
- [x] Foundry loading and operating in embedded browser
- [x] PopOut module functionality with location.hash patch
- [x] Multiple simultaneous popouts
- [x] OS close button interception and sheet return
- [x] JavaScript injection and roll interception

See `/scripts/dice-link/tests/` for test implementations.

---

## Packaging and Deployment

**MVP (v1.0):**
- PyInstaller bundles Python, PyQt6, OpenCV, ONNX Runtime into single .exe (~150-200MB)
- Chromium flags baked into app launch
- Foundry module included in installer (users install into their Foundry instance once)
- ONNX model v1.0.0 embedded
- Auto-update for models

**Future versions:**
- Mac and Linux support
- Additional VTT support (Roll20, D&D Beyond, etc.)
- Account system and cloud sync (v1.1+)

---

## Open Items & Future Considerations

- **Foundry v14 compatibility** — Built-in popout module not yet tested; may require revisiting when Foundry v14 is released
- **Roll20 / D&D Beyond integration** — Approach not yet defined; may require WebSocket extensions or similar embedded browser pattern
- **Multi-monitor setup optimization** — UI layout for controlling dual windows
- **Security model for injected JavaScript** — Formal review needed before production release
- **GDPR compliance** — Still in progress; affects cloud features
- **Account system** — Planned for v1.1+; do not architect for MVP

---

## References

- `ARCHITECTURE-OLD.md` — Original v2.0 architecture (superseded)
- `scripts/dice-link/docs/architecture-decision-embedded-vs-bridge.md` — Detailed technical decision rationale
- `scripts/dice-link/tests/pyqt6-test2-secure-origin.py` — Chromium flags implementation
- `scripts/dice-link/tests/pyqt6-test7-popouts-and-validation.py` — PopOut handling implementation
