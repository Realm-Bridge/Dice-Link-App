# Code Organization TODO

This document tracks code in `main.py` that should be separated into individual scripts for cleaner architecture.

---

## Current State

**main.py** contains ~1166 lines with 10 classes and 2 standalone functions mixed together.

---

## Extraction Order (by dependency level)

Extract one file at a time, test after each extraction.

### Phase 1 - No Internal Dependencies

#### 1. VTTValidator
- **Target file:** `vtt_validator.py`
- **Purpose:** Validates VTT connections and URLs
- **Dependencies:** None (only external imports like `re`)
- **Status:** [ ] Not started

**Testing Criteria:**
- VTTValidator methods work when called from main.py
- URL validation produces correct results
- No import errors

#### 2. ConnectionDialog
- **Target file:** `dialogs.py`
- **Purpose:** UI dialog for VTT connection settings
- **Dependencies:** PyQt6 only, no internal dependencies
- **Status:** [ ] Not started

**Testing Criteria:**
- Dialog opens without errors
- Dialog can be closed
- VTTValidator still works (if called separately)

---

### Phase 2 - Depends on Phase 1 or external only

#### 3. DLABridge
- **Target file:** `dla_bridge.py`
- **Purpose:** Handles QWebChannel communication between DLA and DLC
- **Dependencies:** VTTValidator (for URL validation), PyQt6, bridge_state, debug
- **Status:** [ ] Not started

**Testing Criteria:**
- DLC module initializes and connects successfully
- ConnectionPingReady signal fires every 60 seconds
- receiveConnectionPong slot receives pong responses
- All DLA→DLC signals emit correctly (rollResultReady, diceTrayRollReady, etc.)
- All DLC→DLA slots receive correctly (receiveRollRequest, receiveDiceRequest, etc.)
- 7+ minute idle test: no false disconnects

---

### Phase 3 - Web Engine Components

#### 4. VTT Web Components
- **Target file:** `vtt_web.py`
- **Classes to extract:**
  - `VTTWebPage` - Custom web page class
  - `VTTWebView` - Main VTT web view
  - `VTTPopupView` - Popup web view for character sheets etc.
  - `DraggableWebEngineView` - Main DLA UI browser widget
- **Purpose:** Web engine components for rendering VTT and UI content
- **Dependencies:** PyQt6, DLABridge (for web channel), custom_window
- **Status:** [ ] Not started

**Testing Criteria:**
- Foundry VTT loads in viewing window
- Character sheets open in popup windows
- Drag-and-drop functionality works in main UI
- Web pages render correctly with all content visible
- Console errors are minimal

---

### Phase 4 - Window Components

#### 5. VTT Windows
- **Target file:** `vtt_windows.py`
- **Classes to extract:**
  - `VTTPopupWindow` - Window container for VTT pop-outs
  - `VTTViewingWindow` - Main VTT viewing window
- **Purpose:** Window containers (inherits from CustomWindow)
- **Dependencies:** custom_window.py, VTT Web Components
- **Status:** [ ] Not started

**Testing Criteria:**
- Viewing window opens with custom title bar and buttons
- Popup windows open with custom title bar and buttons
- Window minimize/maximize/close buttons work
- Window titles display correctly (e.g., "Kix" for character sheets)
- Resize functionality works
- Closing viewing window disconnects from Foundry
- Closing popup windows does NOT disconnect

---

### Phase 5 - Controllers

#### 6. WindowController
- **Target file:** `window_controller.py`
- **Purpose:** Manages window lifecycle, VTT connections, popup tracking
- **Dependencies:** VTT Windows, VTT Web Components, DLABridge, ConnectionDialog
- **Status:** [ ] Not started

**Testing Criteria:**
- Application starts without errors
- VTT connection dialog works
- Windows are created and managed correctly
- Popup windows are tracked and managed
- Connection monitor runs continuously
- Ping/pong mechanism functions correctly
- Full end-to-end: connect, load Foundry, roll dice, do nothing for 7+ minutes without disconnect

---

## What Should Remain in main.py

- `run_server()` function - Starts the FastAPI/Uvicorn server
- `main()` function - Application entry point
- App initialization logic (QApplication, browser setup, etc.)
- Imports from extracted modules

---

## Already Separated (Good)

- `custom_window.py` - Generic reusable window components (buttons, title bar, resize grip, CustomWindow base class)
- `bridge_state.py` - Bridge state management and helper functions
- `debug.py` - Debug logging utilities
- `state.py` - Application state management
- `server.py` - FastAPI server and routes
- `config.py` - Configuration constants

---

## Notes

- When extracting, update imports in main.py to import from new modules
- Test after each extraction to ensure nothing breaks
- Watch for circular import issues - may need to reorganize some dependencies
- Each extracted file should have its own imports at the top
