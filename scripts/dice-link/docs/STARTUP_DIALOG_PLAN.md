# Startup Dialog Implementation Plan

## Overview

Replace the current application startup flow with a new Login/VTT Selection dialog that appears before the main DLA window.

**Current Flow:**
1. Main DLA window opens immediately
2. User clicks Connect button → Connection dialog opens
3. User enters VTT IP, validates, connects
4. Theater window opens

**New Flow:**
1. Startup Login Dialog opens first
2. User selects VTT, enters address, enters credentials, clicks Connect
3. Main DLA window AND Theater window open together

---

## Design Specifications

**Window Properties:**
- Width: 550px
- Height: TBD (based on content)
- Style: CustomWindow base class (consistent with existing windows)
- Title: "Dice Link Login"
- Resizable: No
- Draggable: Yes (via title bar)

**Layout (top to bottom, labels left, fields right):**

1. **Title Bar**
   - Dice Link logo (left)
   - Title: "Dice Link Login"
   - Settings button (gear icon)
   - Minimize button
   - Close button

2. **Form Section**
   - "Connect me to:" + Dropdown selector
     - Active: Foundry VTT
     - Greyed out (alphabetical): Beyond Tabletop, Discord, DnD Beyond Maps, Fantasy Grounds, Game Master Engine, Owlbear Rodeo, Roll20, Tabletop Simulator, Tale Spire
   - "VTT Address:" + Text input field (with validation)
   - "User Name:" + Text input field (placeholder: "Usually Email")
   - "Password:" + Password input field

3. **Action Section**
   - "Connect" button (centered)

4. **Footer Section**
   - "Create Free Account" link (left) - opens https://realmbridge.co.uk/
   - Realm Bridge logo (right)

---

## Phase 1: Create StartupDialog UI Framework

**Objective:** Create the basic dialog window with all visual elements (no functionality yet)

**Files to create:**
- `startup_dialog.py` - New file containing StartupDialog class

**Dependencies to check:**
- CustomWindow base class in `custom_window.py`
- Existing logo paths in `static/Logos/`
- Realm Bridge logo availability

**Steps:**

1.1. Read `custom_window.py` to understand CustomWindow structure
1.2. Read `dialogs.py` to understand existing dialog patterns (ConnectionDialog)
1.3. Check available logos in `static/Logos/`
1.4. Create `startup_dialog.py` with:
   - Import statements (verify each import location)
   - StartupDialog class inheriting from CustomWindow
   - Window setup (550px width, non-resizable)
   - Title bar with logo, title, settings, minimize, close
   - Form layout with all labels and fields
   - VTT dropdown with active/greyed options
   - Connect button
   - Footer with link and Realm Bridge logo

**Testing Phase 1:**
- Run app and manually instantiate StartupDialog to verify it displays
- Check all visual elements are present and properly positioned
- Verify dropdown shows Foundry active, others greyed/disabled
- Verify password field masks input

---

## Phase 2: Wire Up Form Functionality

**Objective:** Add functionality to all interactive elements

**Files to modify:**
- `startup_dialog.py` - Add functionality

**Dependencies to check:**
- VTTValidator in `vtt_validator.py` for address validation
- QDesktopServices for opening browser links
- Existing settings functionality

**Steps:**

2.1. Read `vtt_validator.py` to understand validation interface
2.2. Add VTT Address validation on Connect click (reuse VTTValidator)
2.3. Add "Create Free Account" link functionality (open browser to realmbridge.co.uk)
2.4. Add Settings button functionality (placeholder - opens existing settings or shows message)
2.5. Add dropdown change handler (for future VTT-specific behavior)
2.6. Store form values (VTT selection, address, username, password) for use after connect

**Testing Phase 2:**
- Enter invalid VTT address → Should show validation error
- Enter valid VTT address → Should pass validation
- Click "Create Free Account" → Should open browser to realmbridge.co.uk
- Click Settings → Should open settings (or show placeholder)
- Select different VTT options → Greyed ones should not be selectable

---

## Phase 3: Change Application Startup Flow

**Objective:** Make StartupDialog the first window that opens, then launch main DLA + Theater on connect

**Files to modify:**
- `main.py` - Change startup sequence
- `startup_dialog.py` - Add connect success callback

**Dependencies to check:**
- Current main() function structure
- How main DLA window (browser) is created
- How Theater window is launched (VTTViewingWindow)
- WindowController and its role

**Steps:**

3.1. Read `main.py` to understand current startup sequence
3.2. Modify main() to:
   - Create QApplication
   - Show StartupDialog first
   - Wait for user to click Connect
3.3. On successful connect from StartupDialog:
   - Close/hide StartupDialog
   - Launch main DLA window (browser with Flask UI)
   - Launch Theater window (VTTViewingWindow with VTT loaded)
3.4. Pass VTT address from StartupDialog to Theater window
3.5. Handle cancel/close on StartupDialog (exit application)

**Testing Phase 3:**
- Start application → StartupDialog should appear (not main DLA window)
- Close StartupDialog → Application should exit
- Enter valid VTT address and click Connect → Main DLA + Theater should open
- Verify VTT loads in Theater window with the entered address

---

## Phase 4: Final Testing and Cleanup

**Objective:** End-to-end testing and code cleanup

**Steps:**

4.1. Full flow test:
   - Start app fresh
   - See StartupDialog
   - Enter Foundry VTT address
   - Click Connect
   - Verify main DLA window opens
   - Verify Theater window opens with Foundry loaded
   - Verify dice rolls work
   - Verify connection monitoring works

4.2. Edge cases:
   - Invalid VTT address handling
   - Cancel/close at each stage
   - Settings button functionality
   - "Create Free Account" link works

4.3. Code cleanup:
   - Remove any debug logging added during development
   - Verify no unused imports
   - Ensure code follows existing patterns

4.4. Update CODE_ORGANIZATION_TODO.md to reflect new file structure

---

## File Structure After Implementation

```
scripts/dice-link/
├── startup_dialog.py    # NEW - StartupDialog class
├── main.py              # MODIFIED - Changed startup flow
├── custom_window.py     # UNCHANGED - Base class
├── dialogs.py           # UNCHANGED - ConnectionDialog (may be deprecated later)
├── vtt_validator.py     # UNCHANGED - Reused for validation
├── vtt_windows.py       # UNCHANGED - VTTViewingWindow
├── window_controller.py # MAY NEED CHANGES - Depending on how we wire things
└── ...
```

---

## VTT Dropdown Options

**Active (selectable):**
- Foundry VTT

**Greyed Out / Disabled (alphabetical):**
- Beyond Tabletop
- Discord
- DnD Beyond Maps
- Fantasy Grounds
- Game Master Engine
- Owlbear Rodeo
- Roll20
- Tabletop Simulator
- Tale Spire

---

## Notes

- Username/Password fields are placeholders for now - no authentication logic
- Settings button is placeholder - will be updated later with separate functionality
- Only Foundry VTT is functional - other VTTs will be implemented in future phases
- The main DLA window may look different depending on VTT selection in the future
