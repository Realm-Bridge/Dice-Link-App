# Dice Link - External PC Application

## Project Overview

**Dice Link** is a desktop PC application that connects to the Foundry VTT module "Dice Link Companion" (DLC) via WebSocket. Its purpose is to allow tabletop RPG players to use **physical dice** instead of digital dice rolls.

### How It Works

1. A player triggers an action in Foundry VTT (e.g., clicks "Attack" on their character sheet)
2. Foundry generates a roll configuration dialog
3. DLC intercepts this dialog, hides it, extracts all the data, and sends it to Dice Link via WebSocket
4. Dice Link displays the configuration options and dice requirements to the user
5. The user makes any configuration choices and physically rolls their dice
6. Dice Link uses a webcam to detect the dice types and read the results
7. Dice Link sends the results back to DLC
8. DLC injects the results into Foundry and triggers the roll completion
9. The roll appears in Foundry's chat with the physical dice values

### Key Principle

**DLC and Dice Link communicate only through a defined WebSocket message protocol.** Neither needs to know the internal implementation of the other. This keeps the systems decoupled - UI changes, refactoring, or feature additions on either side should not break the connection as long as the message protocol is respected.

---

## Technology Stack (Recommended)

- **Python 3.10+** - Application backend and logic
- **FastAPI** - WebSocket server and HTTP API
- **PyWebView** - Wraps the web UI in a native desktop window (NO browser required)
- **HTML/CSS/JavaScript** - User interface (served by FastAPI, displayed in PyWebView window)
- **OpenCV** - Video capture from webcam
- **NumPy** - Image processing
- **PyInstaller** - Packaging for distribution (Windows .exe, Mac .app, Linux AppImage)
- **OpenCV/TensorFlow** - Dice detection and result reading (future phase)

> **IMPORTANT: This is a desktop application, NOT a web app.** The final product must be a standalone executable that users download and install. It must open its own application window (via PyWebView) - users should NOT need to open a browser or navigate to a URL. The web technologies (HTML/CSS/JS) are used purely for building the UI inside the native window.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DICE LINK (This App)                     │
│                    Python + FastAPI                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend (Python)                            │  │
│  │                                                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│  │  │ WebSocket  │  │   State    │  │   Camera   │    │  │
│  │  │  Manager   │  │  Manager   │  │  Handler   │    │  │
│  │  └────┬───────┘  └──────┬─────┘  └─────┬──────┘    │  │
│  │       │                 │              │           │  │
│  │       └─────────────────┼──────────────┘           │  │
│  │                         │                         │  │
│  │                  ┌──────▼──────┐                  │  │
│  │                  │   Dice      │                  │  │
│  │                  │  Detection  │                  │  │
│  │                  │  (OpenCV)   │                  │  │
│  │                  └─────────────┘                  │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                                  │
│         │  Static files + templates                       │
│         ▼                                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Web UI (HTML/CSS/JavaScript)                        │  │
│  │                                                      │  │
│  │  • Connection Status                                │  │
│  │  • Roll Request Display                             │  │
│  │  • Camera Feed Preview                              │  │
│  │  • Configuration Options                            │  │
│  │  • Result Input/Confirmation                        │  │
│  └──────────────────────────────────────────────────────┘  │
│         △                                                  │
│         │  WebSocket connection                           │
│         │  User interacts via browser                     │
│         │                                                  │
└─────────────────────────────────────────────────────────────┘
         ▲
         │ WebSocket Connection
         │ (ws://localhost:8765)
         ▼
┌─────────────────────────────────────────────────────────────┐
│              FOUNDRY VTT + DLC (External System)            │
│                                                             │
│  DLC connects as a WebSocket CLIENT to Dice Link's server   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Architecture Decisions:**
- FastAPI runs the WebSocket server AND serves the web UI
- All camera, state, and detection logic runs in the same Python process (no inter-process communication overhead)
- PyWebView wraps the HTML/CSS/JS UI in a native desktop window - NO browser required by the user
- Single-threaded async processing via Python's asyncio (handles multiple concurrent connections efficiently)
- The app launches a single window, starts the FastAPI server internally, and loads the UI - exactly like any other desktop application

---

## WebSocket Message Protocol

All messages are JSON objects with a `type` field indicating the message type.

### Connection Management

**DLC → Dice Link: Connection Handshake**
```json
{
  "type": "connect",
  "version": "1.0.0",
  "clientId": "unique-session-id",
  "playerName": "Mike",
  "playerId": "foundry-user-id"
}
```

**Dice Link → DLC: Connection Acknowledged**
```json
{
  "type": "connected",
  "version": "1.0.0",
  "serverName": "Dice Link"
}
```

---

### Roll Request Flow

**DLC → Dice Link: Roll Request**

Sent when a player triggers a roll in Foundry and DLC intercepts the dialog.

```json
{
  "type": "rollRequest",
  "id": "unique-roll-id-12345",
  "timestamp": 1699999999999,
  "player": {
    "id": "foundry-user-id",
    "name": "Mike"
  },
  "roll": {
    "title": "Longsword Attack",
    "subtitle": "Melee Weapon Attack",
    "formula": "1d20 + 5 + 1d4",
    "dice": [
      { "type": "d20", "count": 1 },
      { "type": "d4", "count": 1 }
    ]
  },
  "config": {
    "fields": [
      {
        "name": "attackMode",
        "label": "Attack Mode",
        "type": "select",
        "options": [
          { "value": "oneHanded", "label": "One-Handed" },
          { "value": "twoHanded", "label": "Two-Handed" }
        ],
        "selected": "oneHanded"
      },
      {
        "name": "rollMode",
        "label": "Roll Mode",
        "type": "select",
        "options": [
          { "value": "publicroll", "label": "Public Roll" },
          { "value": "gmroll", "label": "GM Only" },
          { "value": "blindroll", "label": "Blind Roll" },
          { "value": "selfroll", "label": "Self" }
        ],
        "selected": "publicroll"
      },
      {
        "name": "situationalBonus",
        "label": "Situational Bonus",
        "type": "text",
        "value": ""
      }
    ]
  },
  "buttons": [
    { "id": "advantage", "label": "Advantage" },
    { "id": "normal", "label": "Normal" },
    { "id": "disadvantage", "label": "Disadvantage" }
  ]
}
```

**Configuration Fields Reference**

The `config.fields` array contains dynamic form fields that Dice Link must parse and render. Each field has:
- `name` - Internal identifier for tracking changes
- `label` - Display text shown to the user
- `type` - How to render the field (see types below)
- `value` or `selected` - Current value
- Optional field-specific properties (e.g., `options` for select fields)

Supported field types and how to render them:

**Type: `select` (Dropdown)**
- Render as HTML `<select>` element
- `options` array contains objects with `value` and `label`
- `selected` indicates which option is currently chosen
- Example: Attack Mode (One-Handed, Two-Handed), Roll Mode (Public, GM Only, etc.), Ability choices (Strength, Dexterity, etc.)

**Type: `text` (Text Input)**
- Render as HTML `<input type="text">` element
- `value` contains the current text (may be empty string)
- Example: Situational Bonus field for user notes or modifiers

**Type: `number` (Number Input)**
- Render as HTML `<input type="number">` element
- `value` contains the current number
- May have optional `min`, `max`, or `step` properties
- Example: Custom modifier inputs

When the user modifies any field and clicks an action button, send back the changes in `configChanges` object with only the fields that changed (by `name`).

**DLC → Dice Link: Roll Result**

Sent when the user has completed configuration, rolled their dice, and Dice Link has captured the results.

```json
{
  "type": "rollResult",
  "id": "unique-roll-id-12345",
  "timestamp": 1699999999999,
  "buttonClicked": "normal",
  "configChanges": {
    "rollMode": "gmroll",
    "situationalBonus": "+2"
  },
  "results": [
    { "type": "d20", "value": 17 },
    { "type": "d4", "value": 3 }
  ]
}
```

**Dice Link → DLC: Roll Cancelled**

Sent if the user cancels the roll in Dice Link.

```json
{
  "type": "rollCancelled",
  "id": "unique-roll-id-12345",
  "reason": "User cancelled"
}
```

---

### Video Feed (Optional)

**Dice Link → DLC: Video Frame**

If DLC requests video feed, Dice Link can stream frames.

```json
{
  "type": "videoFrame",
  "timestamp": 1699999999999,
  "frame": "data:image/jpeg;base64,/9j/4AAQ..."
}
```

**DLC → Dice Link: Request Video Feed**
```json
{
  "type": "requestVideoFeed",
  "enabled": true,
  "fps": 15
}
```

---

### Error Handling

**Either Direction: Error Message**
```json
{
  "type": "error",
  "code": "INVALID_MESSAGE",
  "message": "Unrecognized message type",
  "relatedId": "unique-roll-id-12345"
}
```

---

## User Interface Requirements

### Main Window

The app should display:

1. **Connection Status** - Indicator showing if DLC is connected or not

2. **Roll Request Panel** (when active) - Rendered from structured JSON data sent by DLC:
   - **Roll Header** - Title (e.g., "Longsword Attack") and subtitle (e.g., "Melee Weapon Attack")
   - **Dice Display** - Visual representation of dice to be rolled:
     - Shows dice types and counts (e.g., "1d20 + 1d4")
     - Use dice SVG icons (provided by DLC) for visual clarity
     - Display the full formula string
   - **Configuration Section** - Dynamic fields based on the dialog from Foundry:
     - Render all `config.fields` from the rollRequest message
     - Support field types: `select` (dropdowns), `text` (text input), `number` (number input)
     - Show labels and available options for each field
     - Allow user to modify values before rolling
   - **Situational Bonus Input** - If present in config
   - **Action Buttons** - Render all buttons from the roll request (e.g., Advantage, Normal, Disadvantage, Critical Hit, etc.)
     - User clicks one to proceed with the roll

3. **Roll In Progress**:
   - Once user clicks an action button, display: "Roll [dice list] now"
   - Show live camera feed for physical dice rolling
   - Display detected results as they're captured

4. **Results Confirmation**:
   - Show detected dice types and values
   - Allow user to confirm or re-roll if detection was incorrect
   - Once confirmed, send results back to DLC

5. **Camera Feed** - Live preview from webcam (in future phases)

### Settings Panel

- **WebSocket Settings**: Host (default: localhost) and port (default: 8765)
- **Camera Selection**: Choose which camera to use
- **Detection Calibration**: Sensitivity settings (future phase)
- **UI Theme**: Light/dark mode toggle

### Design Notes

- The UI should maintain visual consistency with DLC where possible
- Configuration fields should be clearly labeled and easy to interact with
- Action buttons should be prominent and clearly indicate their effect
- The layout should adapt to showing dice first, then camera view once rolling starts

---

## Development Phases

### Phase 1: Core Foundation (MVP)

> **IMPORTANT: Must be built as a desktop application from the start.** Use PyWebView to open a native application window. The app must launch like any other desktop program - double-click to open, shows its own window, no browser required.

- FastAPI WebSocket server on port 8765 (runs internally, user never sees a URL)
- PyWebView desktop window displaying the HTML/CSS/JavaScript UI
- Connection status display (waiting for DLC to connect)
- Receive rollRequest messages from DLC
- Parse and dynamically render dialog from JSON data:
  - Roll title, subtitle, formula, dice list
  - Configuration fields (render dropdowns, text inputs, etc.)
  - Action buttons (Advantage, Normal, Disadvantage, etc.)
- Manual result entry (no camera - user types dice results per die)
- Send rollResult back to DLC
- Basic error handling

**Test Mode (required for Phase 1):**
Since DLC will not be connected during initial development, Phase 1 MUST include a "Test Roll" button visible when no DLC is connected. Clicking it simulates receiving the following rollRequest so the UI can be tested without Foundry running:

```json
{
  "type": "rollRequest",
  "id": "test-roll-001",
  "timestamp": 1699999999999,
  "player": { "id": "test-player", "name": "Test Player" },
  "roll": {
    "title": "Longsword Attack",
    "subtitle": "Melee Weapon Attack",
    "formula": "1d20 + 5 + 1d4",
    "dice": [
      { "type": "d20", "count": 1 },
      { "type": "d4", "count": 1 }
    ]
  },
  "config": {
    "fields": [
      {
        "name": "attackMode",
        "label": "Attack Mode",
        "type": "select",
        "options": [
          { "value": "oneHanded", "label": "One-Handed" },
          { "value": "twoHanded", "label": "Two-Handed" }
        ],
        "selected": "oneHanded"
      },
      {
        "name": "rollMode",
        "label": "Roll Mode",
        "type": "select",
        "options": [
          { "value": "publicroll", "label": "Public Roll" },
          { "value": "gmroll", "label": "GM Only" },
          { "value": "blindroll", "label": "Blind Roll" },
          { "value": "selfroll", "label": "Self" }
        ],
        "selected": "publicroll"
      },
      {
        "name": "situationalBonus",
        "label": "Situational Bonus",
        "type": "text",
        "value": ""
      }
    ]
  },
  "buttons": [
    { "id": "advantage", "label": "Advantage" },
    { "id": "normal", "label": "Normal" },
    { "id": "disadvantage", "label": "Disadvantage" }
  ]
}
```

### Phase 2: Enhanced UI
- Polish dialog rendering (match DLC visual style)
- Configuration field interaction (user can change values)
- Copy dice SVG assets from DLC for visual consistency
- Settings panel (WebSocket host/port, theme, etc.)
- Connection state management (handle reconnects)

### Phase 3: Camera Integration
- Camera selection and preview
- Real-time frame capture
- Video feed streaming back to DLC (optional)
- Display "Roll these dice" during active roll

### Phase 4: Dice Detection & Automation
- Computer vision with OpenCV
- Dice type recognition (d4, d6, d8, d10, d12, d20, d100)
- Dice value reading (pip counting or number recognition)
- Validation (correct dice types rolled?)
- Automatic result capture and submission

---

## Dice Types

Standard RPG dice that must be supported:

| Type | Shape | Values |
|------|-------|--------|
| d4 | Tetrahedron (pyramid) | 1-4 |
| d6 | Cube | 1-6 |
| d8 | Octahedron | 1-8 |
| d10 | Pentagonal trapezohedron | 0-9 or 1-10 |
| d12 | Dodecahedron | 1-12 |
| d20 | Icosahedron | 1-20 |
| d100 | Percentile (two d10s) | 1-100 |

---

## File Structure (Suggested)

```
dice-link/
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Project metadata
├── main.py                   # Entry point
├── app/
│   ├── __init__.py
│   ├── server.py             # FastAPI app setup
│   ├── websocket_handler.py  # WebSocket connection logic
│   ├── state.py              # Roll state management
│   ├── camera.py             # Camera capture and frame handling
│   └── detection.py          # Dice detection logic (future)
├── templates/
│   └── index.html            # Web UI (served by FastAPI)
├── static/
│   ├── css/
│   │   └── style.css         # UI styling
│   ├── js/
│   │   └── client.js         # WebSocket client logic
│   └── dice/                 # Dice SVG icons (from DLC)
├── config.py                 # Configuration (port, paths, etc.)
└── README.md
```

---

## Important Notes

1. **DLC is the WebSocket CLIENT, Dice Link is the SERVER** - This allows DLC to reconnect if Dice Link restarts

2. **Python runs everything in one process** - Camera capture, WebSocket handling, detection, and UI serving all share the same Python runtime (fast and simple)

3. **Desktop application, not a web app** - This must be a standalone desktop application. PyWebView wraps the HTML/CSS/JS UI in a native window. Users install and launch it like any other program - no browser, no URL, no localhost. FastAPI runs internally and is never exposed to the user.

4. **Results must include exact dice types** - DLC needs to know which die produced which value to correctly fulfill the Foundry roll

5. **The message protocol is the contract** - If you need to add new fields, add them as optional to maintain backwards compatibility

6. **Cross-platform by default** - Same Python code runs on Windows, Mac, and Linux. Use PyInstaller to create platform-specific executables for distribution.

7. **Dice SVG assets** - DLC has SVG dice icons in `dice-link-companion/assets/DLC Dice/` that can be copied to Dice Link for visual consistency

---

## Getting Started Prompt

When starting development in a new chat, begin with Phase 1:

"Create a Python desktop application called 'Dice Link' that:
1. Opens as a native desktop window using PyWebView (NOT a browser or localhost URL)
2. Runs a FastAPI WebSocket server on port 8765 internally
3. Displays the HTML/CSS/JavaScript UI inside the PyWebView window
4. Accepts WebSocket connections from DLC clients
5. Displays connection status in the UI
6. Receives 'rollRequest' messages and dynamically renders:
   - Roll title, subtitle and formula
   - Configuration fields (select dropdowns, text inputs) from config.fields array
   - Action buttons (Advantage, Normal, Disadvantage, etc.) from buttons array
7. Includes a 'Test Roll' button (visible when no DLC connected) that injects a mock rollRequest for UI testing
8. Allows manual entry of dice results per die type
9. Sends 'rollResult' messages back when the user submits
10. Is packaged as a standalone executable using PyInstaller for Windows, Mac, and Linux

IMPORTANT: This must behave as a desktop application from day one. Do NOT build it as a web app that requires opening a browser. Use PyWebView to wrap the UI in a native window.

Use the message protocol defined in this document and prioritize clean separation between backend (Python/FastAPI) and frontend (HTML/CSS/JavaScript)."
