# Dice Link — Full Vision Spec

## One-Liner
A cross-platform desktop app that captures physical dice rolls through a camera, recognises the result using the Dice Link ML model, and delivers the outcome to the user's virtual tabletop or other supported software.

---

## Problem Statement
Tabletop RPG players who use virtual tabletop platforms are forced to either roll digital dice or manually type their physical roll results into their VTT. There is no reliable way to roll real physical dice and have that result automatically fed into the game. Dice Link solves this by bridging the physical and digital, keeping the tactile experience of real dice while integrating seamlessly with the software players already use. As part of the wider Dice Link ecosystem, the app also contributes captured dice images to a central server, helping to continuously improve the ML recognition model.

---

## The User
A tabletop RPG player who plays online or uses online tools to support in-person play. Already familiar with at least one VTT (Roll20, Foundry VTT, D&D Beyond Maps, Fantasy Grounds, etc.) and likely uses a voice or video chat system alongside it (Discord, Teams, Zoom, Google Meet, etc.). Owns physical dice — typically a full RPG set — and prefers rolling them over a digital roller.

- **Technical comfort:** Moderate. Comfortable installing desktop software, VTT modules, and browser extensions. Not a developer.
- **Device:** Desktop or laptop PC (Windows, Mac, or Linux), with one or more cameras available — built-in webcam, external USB camera, phone camera, or eventually a dedicated Dice Link camera rig.
- **What they already know:** How to use a VTT, how to roll dice, basic software setup and configuration.
- **What they may be anxious about:** The camera not reading their dice correctly, a wrong result affecting their game, setup being fiddly or slow, disrupting the flow of a session.

---

## Core User Flows

**Flow 1: Session Setup (including first run)**
- User opens Dice Link
- App checks for ML model updates and applies them silently if available
- App prompts for camera selection from available devices
- User selects their camera
- App shows a live camera preview
- User positions their dice area within the frame
- User selects the third party software for this session (e.g. Foundry VTT, Roll20, Discord)
- App asks "Do you want to use a personal dice set?" if any exist
- Session is ready

Note: First run follows the same flow. A dedicated first run experience is to be defined in a future revision.

**Flow 2: Roll Dice and Capture Result**
- App receives a roll request from the third party software, or the user manually configures the roll
- User rolls one or more physical dice
- App automatically detects the dice in the camera feed
- App identifies each die type and face value using the ML model
- Result is displayed clearly in the app (e.g. "d20: 17, d6: 4")
- App waits for user confirmation before sending

**Flow 3: Error Handling**
- Error is triggered in one of two ways: the app flags a recognition issue automatically, or the user flags the result manually
- App displays the error and its best guess at the result
- User reviews the output
- If correct: user confirms; app sends result to the third party software
- If incorrect: user corrects the output; app sends the corrected result to the third party software; app silently captures the misidentified image and the user's correction, packages them, and sends them to the Dice Link server for dataset improvement
- The image upload on error is performed silently and must not interrupt the user's session
- If the server is unavailable, the error package is stored locally until a successful upload can be made, then cleared automatically

**Flow 4: Send Result to Third Party Software**
- User confirms the result
- App packages the result and sends it via the appropriate method for the selected software (VTT module, browser extension, bot, or similar)
- Third party software receives the result and reflects it accordingly
- For Foundry VTT: the companion module intercepts roll requests and routes them to Dice Link via local WebSocket, replacing the native dice roll with the physical result

**Flow 5: Create and Train a Personal Dice Set**
- User opens Dice Link outside of a game session
- User selects "Create New Dice Set"
- User names the dice set (e.g. "My Purple Chessex Set")
- App prompts the user to present each die in turn to the camera
- App captures multiple images of each die across all faces, prompting the user to place the die in different locations in their dice tray to capture varied angles and positions
- Minimum image capture requirements per die face to be confirmed with the ML model team
- App associates the captured images with the dice set
- User repeats for each die in the set
- Dice set is saved locally and synced to the Dice Link server

**Flow 6: Use a Personal Dice Set in a Session**
- During session setup, app asks "Do you want to use a personal dice set?"
- User selects yes and chooses from their saved dice sets
- App loads the personal dice set to assist recognition during the session

**Flow 7: Automatic ML Model Update**
- App checks for available ML model updates on the Dice Link server at launch
- If no update is available, app proceeds to session setup as normal
- If an update is available, app downloads and applies it silently in the background
- If the update completes before the user finishes session setup, it is applied immediately for the current session
- If the update is still in progress when the session begins, it is applied at next launch
- If the server is unavailable, app proceeds with the currently installed model version without interruption
- IMPORTANT: The update mechanism must protect the currently installed model from corruption on a failed or incomplete download. A failed update must leave the existing model fully intact and operational.

---

## Feature List
- Select camera from available devices at session start
- Display live camera preview
- Select target third party software at session start (VTT, Discord, etc.)
- Receive roll request from third party software via local WebSocket
- Manually configure a roll within the app (dice tray UI with buttons and formula bar)
- Automatically detect dice in the camera feed using OpenCV
- Recognise full RPG dice set (d4, d6, d8, d10, d12, d20, d100, etc.)
- Recognise multiple dice in a single capture
- Identify each die type and face value using the Dice Link ONNX ML model
- Display result clearly with a per-die breakdown and visual SVG icons
- Flag recognition errors automatically
- Allow user to flag an incorrect result manually
- Allow user to correct an incorrect result manually with editable formula bar
- Send confirmed result to third party software via local WebSocket
- Silently capture misidentified images and user corrections
- Silently package and upload misidentified data to the Dice Link server
- Check for and silently apply ML model updates at launch
- Create and train personal dice sets
- Load and use a personal dice set during a session
- Store error packages locally until successful server upload, then clear automatically

---

## Scope Boundaries

**Always in scope:**
- Physical dice recognition via camera using ONNX ML inference
- Result delivery to third party software via local WebSocket
- Intercepting and replacing the dice roll function within supported integrations
- Session-based setup and configuration
- Dataset contribution to the Dice Link ML model
- Automatic ML model updates
- Modular, maintainable frontend architecture with vanilla JavaScript

**Eventually in scope (do not build yet):**
- Roll history tracking
- Character sheet management
- Personal dice set creation and training
- Account system and license key integration
- Multiple VTT and software integrations (Roll20, D&D Beyond Maps, Fantasy Grounds, Owlbear Rodeo, Discord, etc.)
- Mac and Linux support
- Mobile and phone camera support
- Dedicated Dice Link camera rig support
- Custom and novelty dice recognition

**Never in scope:**
- Applying game rules or calculations to results
- Replacing VTT functionality beyond the dice rolling function
- Digital dice rolling
- Managing game sessions or player groups

---

## Data Models

**Roll Result**
- Die type detected (e.g. d20)
- Face value detected
- Confidence score from ML model
- Manually overridden (yes/no)
- Corrected die type (if overridden)
- Corrected face value (if overridden)
- Final confirmed value
- Timestamp

**Error Package** — packaged and sent silently to the Dice Link server on any manual correction; stored locally until successfully uploaded, then cleared automatically
- Captured image
- Original die type guess
- Corrected die type value
- Original face value guess
- Corrected face value
- Timestamp

**Session**
- Selected camera device
- Selected third party software
- Session start time
- Personal dice set used (if any)
- List of roll results

**App Settings**
- Last used camera
- Last used third party software
- Personal dice sets (if any created)

**Personal Dice Set** — stored locally and synced to the Dice Link server
- Set ID
- User-defined name
- List of trained die profiles
- Date created
- Date last updated

**Future data models (not yet defined):**
- Roll History
- Character Sheet
- User Account

---

## Key Constraints

**Platform**
- MVP: Windows desktop only (PyWebView + PyInstaller)
- Full vision: Windows, Mac, and Linux desktop; mobile (phone camera); dedicated Dice Link camera rig

**Camera Access**
- Must enumerate and connect to any system-recognised camera device using OpenCV
- Full vision includes phone cameras and a dedicated Dice Link camera rig

**ML Model**
- Runs locally on the user's machine via ONNX Runtime
- Model updates are built and maintained on the Dice Link server
- Updates are pushed automatically and silently to local installations at app launch
- Personal dice datasets are stored locally and synced to the Dice Link server
- IMPORTANT: Update mechanism must protect the local model from corruption on failed or incomplete downloads

**Integrations**
- Dice Link server (AWS) — receives error handling image packages and personal dataset syncs, and pushes ML model updates
- Website hosted via Ionos — future web store for dice and dataset products
- Foundry VTT — via Dice Link companion module, which intercepts roll requests and sends them to the app via local WebSocket
- Other VTTs and software — via browser extensions, bots, or similar methods (to be defined)
- All integration interfaces use local WebSocket protocol for app-to-integration communication
- Integration interfaces with other VTTs and software are to be defined in collaboration with the relevant parallel development teams

**Authentication**
- MVP: no login or accounts required
- Full vision: optional account system, likely linked via a license key, supporting web store purchases and dataset downloads
- Account system is a future consideration — do not architect for it in MVP

**Local Data Storage**
- MVP: JSON files stored in AppData directory for rapid development
- Full Product: SQLite database (deferred to v1.1+)
- Error handling packages must be stored locally until successfully uploaded to AWS, then cleared automatically
- Personal dice datasets stored locally and synced to server

**Performance**
- Recognition must return a result within 3 seconds of roll to result displayed

**Compliance**
- Users must agree to the Dice Link data privacy policy before using server-connected features
- Dice Link is registering with the ICO to legally store user data
- GDPR and international equivalents (e.g. CCPA) are currently under review — do not go live with server-connected features until compliance requirements are confirmed

**Hosting**
- Server infrastructure: AWS
- Website: Ionos

---

## Success Criteria

**Dice Recognition**
- The app correctly identifies all dice types and face values in a single multi-dice capture
- Recognition returns a result within 3 seconds of the dice being placed in frame
- The app correctly flags any result it cannot identify with sufficient confidence

**Error Handling**
- A user can manually correct any misidentified result and send the corrected value without restarting the session
- Misidentified image data and corrections are silently packaged and uploaded to the Dice Link server without interrupting the session
- Error packages are stored locally and successfully uploaded to AWS before being cleared

**VTT Integration**
- A confirmed result appears in Foundry VTT within 3 seconds of the user pressing confirm
- The Foundry companion module successfully intercepts roll requests and routes them to Dice Link via local WebSocket
- Results are delivered correctly via browser extension or equivalent to all supported third party software

**Session Setup**
- A user can complete session setup and make their first successful roll within 5 minutes of opening the app
- The app correctly enumerates all available camera devices on the user's machine using OpenCV

**Server and ML Model**
- ML model updates are pushed and applied automatically without user intervention
- The app continues to function for core recognition and result delivery during a server outage

**User Interface**
- The dice tray provides a clean, responsive interface for manual formula entry or button-based dice selection
- Users can edit formulas directly in the formula bar for full control over roll construction
- Visual SVG dice icons clearly represent die types
- The UI transitions smoothly between roll window and dice entry states

**Personal Dice Sets (future)**
- A user can create, name, and train a personal dice set within the app
- Personal dice sets improve recognition accuracy for the user's specific dice over time
- Personal dice sets are synced successfully between the local machine and the Dice Link server

---

## Open Items — Resolve Before Building

- **First run experience:** A dedicated first run setup flow has not yet been defined. Currently treated as the same as session setup.
- **Minimum training images:** The minimum number of images required per die face during personal dice set training must be confirmed with the ML model team.
- **Integration interfaces:** The exact communication interfaces between the desktop app and browser extensions and any bots are to be defined with the parallel development teams. Foundry VTT integration is already defined via local WebSocket protocol.
- **GDPR compliance:** Full compliance requirements are under review. ICO registration is in progress. No server-connected features should go live until this is resolved.
- **Account system:** Planned for future but not yet designed. Do not architect for it in MVP.
