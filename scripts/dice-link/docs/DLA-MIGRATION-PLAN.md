# DLA Migration Plan: Embedded Browser Architecture

**Version:** 3.0  
**Date:** April 23, 2026  
**Status:** Draft - Ready for Implementation  

---

## Current State Summary

**What DLA currently does:**
1. PyQt5 frameless window displaying a local FastAPI web UI
2. FastAPI server with WebSocket endpoints for DLC communication
3. UI for dice tray, roll requests, player modes, settings
4. UPnP port forwarding support

**What we're migrating to:**
1. PyQt6 (required for Chromium version supporting CSS Cascade Layers)
2. Native Qt widgets for controls UI (not web UI)
3. Separate embedded Foundry/Roll20 browser window (QMainWindow)
4. Direct JavaScript injection for DLC-VTT communication
5. PopOut window handling for character sheets

---

## Migration Phases

### Phase 1: PyQt5 to PyQt6 Upgrade

**Goal:** Update existing DLA to run on PyQt6

**Rationale:** PyQt5's Chromium 83 doesn't support CSS Cascade Layers (requires Chromium 99+). Foundry v13+ uses CSS Cascade Layers. PyQt6 has newer Chromium version.

**Tasks:**
1. Update imports from PyQt5 to PyQt6
2. Update enum syntax: `Qt.FramelessWindowHint` → `Qt.WindowType.FramelessWindowHint`
3. Update signal/slot connection syntax if needed
4. Test that existing UI still works with native widgets

**Test Point:**
- [ ] Run DLA, confirm frameless controls window appears with dice tray UI
- [ ] Confirm window controls (minimize, close, drag) work
- [ ] No console errors from Qt library

---

### Phase 2: Connection UI with Validation

**Goal:** Create controls window with connection dialog

**Current Behavior:** DLA launches with only controls window. Viewing window does not exist until user connects to a VTT.

**Tasks:**
1. Create "Connect" button in controls window
2. Button opens popup dialog for URL entry
3. User enters URL (e.g., `http://83.105.151.227:30000/`)
4. DLA validates URL by:
   - Making HTTP request to URL
   - Checking response headers/content for Foundry or Roll20 signature
5. If valid: Close dialog, launch viewing window with URL
6. If invalid: Show error message in dialog, allow retry
7. Store last valid URL for future sessions (optional)

**Test Point:**
- [ ] "Connect" button opens popup dialog
- [ ] Can type URL in dialog
- [ ] DLA validates `http://83.105.151.227:30000/` as Foundry
- [ ] Viewing window appears showing Foundry login page
- [ ] Invalid URL shows error, dialog stays open
- [ ] Closing dialog doesn't crash app

---

### Phase 3: Foundry Viewing Window with Security Bypass

**Goal:** Create separate window with embedded Foundry, apply Chromium flags

**Tasks:**
1. Create `FoundryBrowserWindow` class (QMainWindow with QWebEngineView)
2. Create custom `QWebEnginePage` subclass to override `createWindow()`
3. Pass Chromium flags via `sys.argv` to `QApplication()`:
   ```
   --unsafely-treat-insecure-origin-as-secure={origin}
   --disable-web-security
   --disable-features=CrossOriginOpenerPolicy
   --disable-features=CrossOriginEmbedderPolicy
   --allow-running-insecure-content
   --disable-site-isolation-trials
   --disable-features=IsolateOrigins
   --disable-features=site-per-process
   --test-type
   --ignore-certificate-errors
   ```
4. Load Foundry URL in QWebEngineView
5. Implement navigation control: block external navigation, only allow Foundry domain

**Verification:**
- Run in Foundry console: `console.log(window.isSecureContext)` - should print `true`

**Test Point:**
- [ ] Viewing window appears and loads Foundry
- [ ] Can log into Foundry
- [ ] Can open character sheets, browse tabs
- [ ] Foundry's own features work (no permission errors)
- [ ] External links don't navigate away from Foundry

---

### Phase 4: PopOut Window Handling

**Goal:** Make Foundry PopOut module work correctly

**Tested on:** Foundry v13 with third-party PopOut module  
**Note:** Foundry v14 built-in popout not yet tested - may need revisiting

**Tasks:**
1. In custom `QWebEnginePage`, override `createWindow()` to handle popup requests
2. Create `PopupWindow` class (QMainWindow with PopupBridge)
3. Inject `window.open()` patch into Foundry page (adds `.location` property):
   - Patch must run BEFORE PopOut module initializes
   - Hook into page load finished event
4. Implement `PopupWindow.closeEvent()` interception:
   - Click sheet's close button (`[data-action="close"]`) instead of immediately closing
   - Wait 300-500ms for PopOut's unload handler to return sheet to main window
   - Then close the popup window
   - Use `is_closing` flag to prevent double-close

**Reference:** See `architecture-decision-embedded-vs-bridge.md` section "Foundry PopOut Module Integration" for complete implementation details

**Test Point:**
- [ ] Pop out a character sheet - displays correctly in separate window
- [ ] Close with OS close button (red X) - sheet returns to main, popup closes
- [ ] Close with sheet close button (blue X) - same behavior
- [ ] Multiple popouts work independently
- [ ] Console shows [PATCH] and [POPUP] log messages confirming patches active

---

### Phase 5: DLC-Foundry Communication Bridge

**Goal:** Enable DLC module to send/receive messages from DLA

**Tasks:**
1. Create JavaScript injection script for Foundry page
2. Inject after Foundry loads (hook into `page.loadFinished` signal)
3. Establish communication channel:
   - Foundry page runs DLC module (existing code)
   - Injected JS provides `window.dlaInterface` object with methods
   - DLC module can call `window.dlaInterface.sendRollResult(data)`
   - DLA can call `page.runJavaScript()` to send data to Foundry
4. Test end-to-end: Roll in Foundry → appears in DLA controls → result back to Foundry chat

**Instructions for DLC Chat (Required Updates to DLC Module):**

The DLC Foundry module must be updated to work with the embedded browser approach:

1. **Remove WebSocket Client Code**
   - Delete/disable any code that connects to DLC WebSocket server
   - The DLC module no longer needs to establish its own connection to DLA

2. **Add DLA Interface Detection**
   - At module initialization, check for `window.dlaInterface` object
   - If present, DLA is embedded; use `window.dlaInterface` for communication
   - If absent, fall back to old WebSocket approach (for standalone Foundry)

3. **Replace WebSocket Emit with DLA Interface**
   - Old: `socket.emit("dice-link.roll-result", data)`
   - New: `if (window.dlaInterface) window.dlaInterface.sendRollResult(data)`

4. **Listen for DLC Requests**
   - Old: Listen on WebSocket for incoming messages
   - New: Register callback on `window.dlaInterface`:
     ```javascript
     if (window.dlaInterface) {
       window.dlaInterface.onRollRequest = function(data) {
         // Handle roll request from DLA
       };
     }
     ```

5. **Broadcast to Players**
   - Continue using `game.socket.emit()` to broadcast to all players in Foundry
   - This works the same way whether embedded or standalone

6. **Module Configuration**
   - No changes needed to `module.json`
   - Module should detect DLA vs WebSocket at runtime

**Example Implementation Pattern:**
```javascript
// In DLC module initialization
Hooks.once('init', () => {
  const isDLAEmbedded = typeof window.dlaInterface !== 'undefined';
  
  if (isDLAEmbedded) {
    console.log('DLC: Running embedded in DLA');
    // Use window.dlaInterface for communication
  } else {
    console.log('DLC: Running standalone, using WebSocket');
    // Use existing WebSocket code
  }
});
```

**Test Point:**
- [ ] DLC module detects DLA embedded browser (console shows "Running embedded in DLA")
- [ ] Roll initiated in Foundry → appears in DLA controls window
- [ ] Dice result from DLA → appears in Foundry chat for all players
- [ ] Multiple players see the same result in chat
- [ ] No console errors from DLC module

---

### Phase 6: Remove Obsolete Code

**Goal:** Clean up code no longer needed

**Tasks:**
1. Remove WebRTC handshake endpoints (no longer used)
2. Remove UPnP code (not needed for embedded browser)
3. Review FastAPI server - may be able to remove if no other endpoints needed
4. Update config.py to remove obsolete settings
5. Update requirements.txt - remove unused dependencies

**Test Point:**
- [ ] Full workflow: Foundry roll → DLA controls → result in Foundry chat
- [ ] No console errors or warnings
- [ ] No hanging processes on shutdown
- [ ] Clean shutdown of both windows

---

## Decision Log

### Question 1: Connection UI Approach
**Decision:** Use "Connect" button → popup dialog for URL entry  
**Rationale:** Separates connection concerns from main controls UI; allows validation before opening viewing window; can iterate on UI/UX easily

### Question 2: Controls UI Technology
**Decision:** Native Qt widgets (not FastAPI web UI)  
**Rationale:** Faster runtime performance; avoids debugging web UI issues; native controls are more responsive; simplifies deployment (no web server needed for controls)

### Question 3: Window Startup
**Decision:** Only viewing window opens on demand after connection validation  
**Rationale:** Cleaner startup; DLA can run without a Foundry instance; user has explicit control over when to connect

---

## Testing Checklist

- [ ] Phase 1: PyQt6 upgrade, all existing UI works
- [ ] Phase 2: Connection dialog works, validation works
- [ ] Phase 3: Foundry loads, isSecureContext is true, navigation blocked
- [ ] Phase 4: PopOut windows work, multiple popouts independent
- [ ] Phase 5: DLC module detects DLA, rolls flow end-to-end
- [ ] Phase 6: No obsolete code, clean shutdown
- [ ] Full workflow: Login → roll → result appears for all players
- [ ] Can close viewing window without crashing controls window
- [ ] Can reconnect to different Foundry instance

---

## Implementation Order

1. Phase 1 (Foundation)
2. Phase 2 (UI)
3. Phase 3 (Browser Window)
4. Phase 4 (PopOut)
5. Phase 5 (Integration)
6. Phase 6 (Cleanup)

Each phase should have all test points passing before moving to next phase.

---

## External IP for Testing

`http://83.105.151.227:30000/`

Use this URL when testing Phase 2 validation and Phase 3 browser loading.

---

## Reference Documents

- `ARCHITECTURE.md` - New v3.0 architecture
- `ARCHITECTURE-OLD.md` - Previous v2.0 architecture
- `architecture-decision-embedded-vs-bridge.md` - Detailed decision rationale
  - Section: Qt WebEngine Chromium Flags (line 420)
  - Section: Foundry PopOut Module Integration (line 511)
