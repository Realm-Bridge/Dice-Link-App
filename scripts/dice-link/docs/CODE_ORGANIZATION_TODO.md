# Code Organization TODO

This document tracks code in `main.py` that should be separated into individual scripts for cleaner architecture.

---

## Current State

**main.py** contains ~1161 lines with 10 classes and 2 standalone functions mixed together.

---

## Classes to Extract

### 1. VTT Validation
- **Class:** `VTTValidator` (line 31)
- **Target file:** `vtt_validator.py`
- **Purpose:** Validates VTT connections and URLs

### 2. Bridge/Communication
- **Class:** `DLABridge` (line 94)
- **Target file:** `dla_bridge.py`
- **Purpose:** Handles communication between DLA and VTT

### 3. VTT Web Engine Components
- **Classes:**
  - `VTTWebPage` (line 387)
  - `VTTWebView` (line 551)
  - `VTTPopupView` (line 775)
  - `DraggableWebEngineView` (line 954)
- **Target file:** `vtt_web.py`
- **Purpose:** Web engine components for rendering VTT content

### 4. VTT Window Components
- **Classes:**
  - `VTTPopupWindow` (line 434)
  - `VTTViewingWindow` (line 507)
- **Target file:** `vtt_windows.py`
- **Purpose:** Window containers for VTT views (inherits from CustomWindow)

### 5. Connection Dialog
- **Class:** `ConnectionDialog` (line 799)
- **Target file:** `dialogs.py`
- **Purpose:** UI dialog for VTT connection settings

### 6. Window Controller
- **Class:** `WindowController` (line 879)
- **Target file:** `window_controller.py`
- **Purpose:** Manages window lifecycle and coordination

---

## What Should Remain in main.py

- `run_server()` function (line 1013)
- `main()` function (line 1024)
- App initialization and entry point logic
- `DLCBridgeApp` class (main application class)

---

## Already Separated (Good)

- `custom_window.py` - Generic reusable window components (buttons, title bar, resize grip, CustomWindow base class)
- `bridge_state.py` - Bridge state management
- `log_vtt.py` - VTT logging utilities

---

## Suggested Extraction Order

1. `vtt_validator.py` - No dependencies on other main.py classes
2. `dla_bridge.py` - Depends on vtt_validator
3. `vtt_web.py` - Web engine components
4. `vtt_windows.py` - Window classes (depends on custom_window.py)
5. `dialogs.py` - Connection dialog
6. `window_controller.py` - Window management

---

## Notes

- When extracting, update imports in main.py
- Test after each extraction to ensure nothing breaks
- Keep circular import dependencies in mind
