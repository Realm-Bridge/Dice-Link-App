# Architecture Comparison: Patent Spec vs MVP Implementation

## Overview

This document compares the architecture in your partner's patent documents (ARCHITECTURE.md + SPEC.md) against the MVP architecture we've been building. The goal is to align both approaches and identify necessary changes.

---

## Key Differences Summary

| Aspect | Patent Spec | MVP (What We Built) | Recommendation |
|--------|-------------|---------------------|----------------|
| **Desktop Shell** | Electron | PyWebView | **Use PyWebView** - lighter, faster startup |
| **App Language** | TypeScript + React | Python + Vanilla JS | **Keep Python + Vanilla JS** - already working, simpler |
| **ML Inference** | onnxruntime-node (in Electron) | ONNX Runtime (Python) | **Keep Python ONNX** - same result, native Python integration |
| **Camera Access** | Web APIs (getUserMedia) | OpenCV (cv2) | **Keep OpenCV** - better control, Python-native |
| **Local Storage** | SQLite via better-sqlite3 | File-based JSON + AppData | **Consider SQLite** for full version, JSON fine for MVP |
| **VTT Module Name** | "foundry-module" | "dice-link-companion" | **Align naming** - use consistent naming |
| **ML Training Location** | Separate workstream, never shipped | Server-side, ONNX exported to users | **Already aligned** |

---

## Detailed Analysis

### 1. Desktop App Shell: Electron vs PyWebView

**Patent Spec says:** Electron (Windows MVP, expand to Mac/Linux)

**We decided:** PyWebView + Python

**Why our choice is better for this project:**
- **Electron drawbacks:**
  - Bundles entire Chromium (~150-300MB install size)
  - Slower startup (loading Chromium takes time)
  - Higher memory footprint
  - Requires Node.js knowledge for backend
  
- **PyWebView advantages:**
  - Uses native OS webview (much smaller footprint)
  - Faster startup
  - Python backend integrates naturally with OpenCV and ONNX
  - Smaller deployment (~100-150MB total including ML model)
  - Your ML specialist likely knows Python already

**Recommendation:** Update patent spec to use PyWebView. The user experience is identical (native window with web UI), but the technical benefits are significant for a camera/ML app.

---

### 2. App Language: TypeScript+React vs Python+Vanilla JS

**Patent Spec says:** TypeScript throughout, React for UI

**We built:** Python (FastAPI backend), Vanilla JavaScript (frontend)

**Analysis:**
- React adds complexity and bundle size for marginal benefit in this app
- Vanilla JS with our modular structure (state.js, websocket.js, ui/*.js) is maintainable
- Python backend is essential for OpenCV/ONNX - having TypeScript in Electron would require bridging

**Recommendation:** Update patent spec to reflect Python backend + Vanilla JS frontend. The architecture we have is simpler and works.

---

### 3. Camera Access: getUserMedia vs OpenCV

**Patent Spec says:** Web APIs (getUserMedia) built into Electron

**We built:** OpenCV (cv2) with DirectShow backend

**Analysis:**
- getUserMedia is limited - browser-level API with less control
- OpenCV gives direct camera access, frame manipulation, preprocessing for ML
- OpenCV is industry standard for computer vision tasks
- Your ML model will expect OpenCV-formatted frames

**Recommendation:** Update patent spec to use OpenCV. This is the correct choice for a computer vision application.

---

### 4. Local Storage: SQLite vs File-based

**Patent Spec says:** SQLite via better-sqlite3

**We built:** File-based JSON storage in AppData

**Analysis:**
- For MVP, JSON files are sufficient (settings, training queue)
- For full product with Session history, Roll history, Personal Dice Sets - SQLite makes sense
- SQLite works fine with Python (sqlite3 built-in)

**Recommendation:** Keep file-based for MVP. Plan for SQLite migration when adding:
- Roll history tracking
- Session management
- Personal dice set storage

---

### 5. Cloud Infrastructure

**Patent Spec says:** AWS S3 + Lambda + API Gateway

**We specified:** Generic "Realm Bridge servers" with REST API

**Analysis:**
- Both approaches are compatible
- AWS is a reasonable choice
- The API endpoints we defined align with what Lambda functions would provide

**Recommendation:** Keep AWS infrastructure as specified in patent. Our packaging spec's API endpoints map directly to Lambda functions:
- `GET /dla/model/latest` → check-model-update Lambda
- `POST /dla/training/upload` → receive-error-package Lambda
- Dice set sync → sync-dice-set Lambda

---

### 6. Foundry Module Communication

**Patent Spec says:** "Local WebSocket server runs inside Electron app"

**We built:** WebSocket server runs in DLA (Python/FastAPI), DLC connects to it

**Analysis:**
- Same concept, different implementation
- Our two-phase communication protocol (rollRequest → buttonSelect → diceRequest → diceResult) is more detailed than the spec
- This is good - we've already defined the integration interface the spec left as "open item"

**Recommendation:** Add our communication protocol to the patent spec. It's the "integration interface" they said needed to be defined.

---

## Data Models Comparison

### Patent Spec Data Models

| Model | Purpose | MVP Status |
|-------|---------|------------|
| RollResult | Single die outcome | **Not implemented yet** - rolls go direct to Foundry |
| ErrorPackage | Training data on corrections | **Implemented** as training_queue JSON |
| Session | Game session tracking | **Not implemented** - not needed for MVP |
| AppSettings | User preferences | **Implemented** as config.json |
| PersonalDiceSet | Custom dice training | **Not implemented** - future feature |
| DieProfile | Per-die training data | **Not implemented** - future feature |
| TrainingImage | Captured training frame | **Implemented** in training_queue structure |

**Recommendation:** Our simplified data models are correct for MVP. The full data models from the patent spec should be implemented when adding:
- Roll history
- Session management  
- Personal dice sets

---

## Project Structure Comparison

### Patent Spec Structure
```
dice-link/
├── app/                  # Electron + React
├── ml/                   # ML training (Python)
├── server/               # AWS Lambda
├── foundry-module/       # Foundry VTT module
└── browser-extension/    # Future
```

### Our Current Structure
```
dice-link/
├── dice-link-companion/  # Foundry VTT module (DLC)
├── scripts/dice-link/    # Desktop app (DLA) - Python + PyWebView
└── [server TBD]          # AWS Lambda (not yet built)
```

**Recommendation:** Restructure to align naming:
```
dice-link/
├── app/                  # Desktop app (PyWebView + Python) - rename from scripts/dice-link
├── ml/                   # ML training workstream
├── server/               # AWS Lambda functions
├── foundry-module/       # Foundry VTT module (rename from dice-link-companion)
└── browser-extension/    # Future
```

---

## Recommended Changes to Patent Documents

### ARCHITECTURE.md Changes

1. **Tech Stack table - replace:**
   ```
   | Desktop app shell | Electron | → | Desktop app shell | PyWebView |
   | App language | TypeScript | → | App language | Python (backend), JavaScript (frontend) |
   | App UI | React | → | App UI | Vanilla JavaScript + HTML/CSS |
   | Camera access | Web APIs | → | Camera access | OpenCV (cv2) |
   | Local storage | SQLite via better-sqlite3 | → | Local storage | SQLite via sqlite3 (Python) |
   ```

2. **Project structure - update app/ folder:**
   ```
   app/
   ├── main.py                    # Entry point - starts PyWebView
   ├── config.py                  # Configuration
   ├── app/
   │   ├── server.py              # FastAPI server
   │   ├── websocket_handler.py   # Message handling
   │   ├── state.py               # State management
   │   └── camera.py              # OpenCV camera
   ├── models/                    # ONNX model storage
   ├── templates/
   │   └── index.html             # UI template
   ├── static/
   │   ├── js/                    # Modular JavaScript
   │   │   ├── client.js
   │   │   ├── state.js
   │   │   ├── websocket.js
   │   │   └── ui/
   │   ├── css/
   │   └── DLC Dice/              # SVG assets
   └── requirements.txt
   ```

3. **Environment variables - update for Python:**
   - Remove Node/Electron-specific vars
   - Keep API vars the same

4. **Add Integration Protocol section:**
   - Include our full WebSocket message format documentation
   - This fills the "Open Item" about integration interfaces

### SPEC.md Changes

1. **Tech constraints - update:**
   - Change "Electron" references to "PyWebView"
   - Change "TypeScript" to "Python"

2. **Add clarification to "Never in scope":**
   - "Digital dice rolling" - clarify this means NO fallback digital rolling. The dice tray in DLA is for physical dice entry, not digital rolling.

3. **Update performance constraints:**
   - Recognition within 3 seconds is correct
   - Add: "App startup under 5 seconds" (achievable with PyWebView, harder with Electron)

---

## Alignment Summary

### What's Already Aligned
- ML inference uses ONNX Runtime (just different language bindings)
- Training happens server-side, not on user machines
- Error packages collected and uploaded
- Foundry module intercepts rolls
- AWS infrastructure for server
- Privacy consent required
- MVP is Windows-first

### What Needs Patent Spec Updates
- Desktop shell: Electron → PyWebView
- Language: TypeScript/React → Python/Vanilla JS
- Camera: getUserMedia → OpenCV
- Add: Complete WebSocket protocol documentation
- Add: Two-phase communication flow (Phase A: config, Phase B: dice)

### What We Should Add to MVP Later
- SQLite for full data model support
- Session tracking
- Roll history
- Personal dice sets
- Mac/Linux support

---

## Next Steps

1. **Share this document with your partner** for review
2. **Decide together** if patent docs should be updated before submission
3. **ML specialist** should review both docs when they join
4. **Continue MVP development** - our architecture is sound for the product goals

The good news: Our MVP architecture is not contradicting the vision - it's a more practical implementation of the same goals. The changes are technical choices, not product direction changes.
