# Dice Link — Architecture Overview

**Version 2.0 | April 2026**
**Realm Bridge Ltd. | Confidential**

---

## What This Document Covers

This document describes the technical architecture for the Dice Link desktop application. It covers the chosen tech stack, project structure, environment variables, and data models. It is intended as a reference for developers joining the project.

For product scope and user flows, refer to the Full Vision Specification.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Desktop app shell | PyWebView | Windows/Mac/Linux; lighter than Electron, Python integrates natively |
| App backend | Python + Flask | Handles WebSocket comms, camera access, inference, database, uploads |
| App frontend | Vanilla JavaScript | Rendered in PyWebView browser context; modular and performant |
| Frontend UI framework | Custom CSS + Semantic HTML | No framework overhead; clean separation of concerns |
| ML training | Python + PyTorch + YOLO v11 | Separate workstream; never shipped to users |
| ML inference | ONNX Runtime (Python) | Runs exported YOLO v11 model locally within Flask backend |
| Camera access | OpenCV (Python) | System-level camera enumeration and capture; more flexible than web APIs |
| Local storage | JSON files (MVP) → SQLite (full product) | JSON for rapid MVP development; SQLite deferred to v1.1+ |
| Cloud storage | AWS S3 | Stores ML model files, error packages, and personal dice set syncs |
| Cloud API | AWS Lambda + API Gateway | Serverless; three functions (see Server section below) |
| VTT / extension comms | Local WebSocket server | Runs inside the Flask backend on localhost |
| Foundry VTT module | JavaScript | Intercepts roll requests and routes them to the app via WebSocket |
| Browser extensions | JavaScript / TypeScript | Connects other VTTs and software to the app via WebSocket |

---

## Hybrid Data Flow

The system uses a hybrid architecture where ML training happens on Realm Bridge servers (using PyTorch/YOLO v11), while inference runs locally on the user's machine (using ONNX Runtime). Training data flows up to the server; updated models flow down to users.

```
┌─────────────────────────────────────────────────────────────────┐
│                    REALM BRIDGE SERVERS                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Receive    │───▶│   Train     │───▶│  Export to  │         │
│  │  User Data  │    │   Model     │    │    ONNX     │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         ▲                                     │                 │
│         │                                     ▼                 │
│         │                           ┌─────────────────┐        │
│         │                           │  Model Server   │        │
│         │                           │  (hosts .onnx)  │        │
│         │                           └─────────────────┘        │
└─────────│─────────────────────────────────────│────────────────┘
          │                                     │
          │ Upload training data                │ Download model updates
          │ (on app close)                      │ (on app open)
          │                                     │
┌─────────│─────────────────────────────────────│────────────────┐
│         │              USER PC (DLA)          ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Capture   │───▶│  ONNX       │───▶│   Send to   │        │
│  │   Dice      │    │  Inference  │    │   Foundry   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                                                      │
│         ▼                                                      │
│  ┌─────────────┐                                               │
│  │  Store for  │  (images + metadata stored locally)          │
│  │  Training   │                                               │
│  └─────────────┘                                               │
└────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
dice-link/
├── app/                        # Desktop application (Flask backend + JS frontend)
│   ├── app.py                  # Flask server entry point
│   ├── config.py               # Configuration management
│   ├── requirements.txt         # Python dependencies
│   ├── templates/
│   │   └── index.html          # Main HTML shell
│   ├── static/
│   │   ├── js/
│   │   │   ├── client.js       # WebSocket client and message router
│   │   │   ├── state.js        # Centralized state management
│   │   │   ├── utils.js        # Shared utility functions
│   │   │   ├── websocket.js    # WebSocket connection handling
│   │   │   └── ui/
│   │   │       ├── roll-window.js       # Roll window states and rendering
│   │   │       ├── dice-tray.js         # Dice button controls and formula bar
│   │   │       ├── dice-entry.js        # SVG dice face selection
│   │   │       ├── settings.js          # Settings panel
│   │   │       └── connection.js        # Connection status UI
│   │   ├── css/
│   │   │   └── style.css       # All styling (semantic colors and variables)
│   │   └── DLC Dice/           # SVG dice icon assets
│   │       ├── D4/, D6/, D8/, D10/, D12/, D20/, D100/
│   │       └── [blank and selected variants for each die]
│   ├── core/
│   │   ├── camera.py           # Camera enumeration and frame capture (OpenCV)
│   │   ├── inference.py        # ONNX model inference and dice recognition
│   │   ├── websocket_handler.py # WebSocket message handling and routing
│   │   └── storage.py          # Local file/database operations
│   └── scripts/                # Build and packaging scripts
│       └── build_exe.py        # PyInstaller configuration
├── ml/                         # ML training workstream (not shipped to users)
│   ├── data/
│   │   ├── raw/
│   │   └── annotated/
│   ├── training/
│   │   ├── train.py
│   │   ├── export.py           # Exports PyTorch model to ONNX
│   │   └── evaluate.py
│   ├── models/                 # Exported ONNX files output here
│   ├── requirements.txt
│   └── README.md
├── server/                     # AWS Lambda functions
│   ├── functions/
│   │   ├── check-model-update/
│   │   ├── receive-error-package/
│   │   └── sync-dice-set/
│   ├── package.json
│   └── template.yaml
├── foundry-module/             # Foundry VTT companion module
│   ├── src/
│   │   ├── module.js           # Foundry module entry point
│   │   └── websocket-client.js # WebSocket client for local app connection
│   ├── lang/
│   └── module.json
├── browser-extension/          # Browser extension (other VTTs and software)
└── README.md
```

---

## Environment Variables

### Desktop App (`app/`)

| Variable | Purpose |
|---|---|
| `DICE_LINK_ENV` | Whether the app is running in development or production |
| `DICE_LINK_WEBSOCKET_PORT` | The local port the WebSocket server listens on (e.g. 43560) |
| `DICE_LINK_API_BASE_URL` | The base URL of the AWS API Gateway |
| `DICE_LINK_API_KEY` | The key that authenticates the app to the AWS API |
| `DICE_LINK_APPDATA_PATH` | Path to AppData directory for model storage and user data (set at runtime) |

### AWS Lambda (`server/`)

| Variable | Purpose |
|---|---|
| `AWS_REGION` | Which AWS region the infrastructure lives in |
| `S3_BUCKET_MODELS` | S3 bucket for ML model files |
| `S3_BUCKET_ERROR_PACKAGES` | S3 bucket for uploaded error image packages |
| `S3_BUCKET_DICE_SETS` | S3 bucket for personal dice set syncs |
| `MODEL_MANIFEST_KEY` | Path within the models bucket to the version manifest file |

### ML Training (`ml/`)

| Variable | Purpose |
|---|---|
| `TRAINING_DATA_PATH` | Path to annotated training images on the ML expert's machine |
| `MODEL_OUTPUT_PATH` | Where the finished exported ONNX model file is saved |
| `YOLO_EPOCHS` | Number of training runs to perform |
| `YOLO_CONFIDENCE_THRESHOLD` | Minimum confidence score for a result to be considered valid |

`DICE_LINK_API_KEY` and `DICE_LINK_API_BASE_URL` must never be hardcoded in source. Store them in a `.env` file and ensure `.env` is listed in `.gitignore`.

---

## Data Models

### RollResult
Represents a single die's outcome within a session.

```
RollResult {
  id                   : UUID      [required, primary key, auto-generated]
  session_id           : UUID      [required, foreign key -> Session.id]
  die_type_detected    : ENUM(d4, d6, d8, d10, d10_percentile, d12, d20, d100)
                                   [required]
  face_value_detected  : INTEGER   [required, min: 1]
  confidence_score     : FLOAT     [required, range: 0.0 - 1.0]
  is_overridden        : BOOLEAN   [required, default: false]
  die_type_corrected   : ENUM(d4, d6, d8, d10, d10_percentile, d12, d20, d100)
                                   [nullable, present only if is_overridden = true]
  face_value_corrected : INTEGER   [nullable, present only if is_overridden = true, min: 1]
  final_die_type       : ENUM(d4, d6, d8, d10, d10_percentile, d12, d20, d100)
                                   [required, equals die_type_corrected if overridden,
                                    else die_type_detected]
  final_face_value     : INTEGER   [required, equals face_value_corrected if overridden,
                                    else face_value_detected]
  timestamp            : DATETIME  [required, UTC, auto-generated on creation]
}
```

### ErrorPackage
Created silently on any manual correction. Queued locally and uploaded to S3, then deleted on confirmed upload.

```
ErrorPackage {
  id                         : UUID      [required, primary key, auto-generated]
  roll_result_id             : UUID      [required, foreign key -> RollResult.id]
  image_data                 : BLOB      [required, captured frame at time of roll]
  die_type_original_guess    : ENUM(d4, d6, d8, d10, d10_percentile, d12, d20, d100)
                                         [required]
  die_type_corrected         : ENUM(d4, d6, d8, d10, d10_percentile, d12, d20, d100)
                                         [required]
  face_value_original_guess  : INTEGER   [required, min: 1]
  face_value_corrected       : INTEGER   [required, min: 1]
  timestamp                  : DATETIME  [required, UTC, auto-generated on creation]
  upload_status              : ENUM(pending, uploaded)
                                         [required, default: pending]
  uploaded_at                : DATETIME  [nullable, set when upload_status = uploaded]
}
NOTE: Records where upload_status = uploaded must be purged automatically
after confirmed successful upload to S3.
```

### Session
Represents a single game session from open to close.

```
Session {
  id                  : UUID      [required, primary key, auto-generated]
  camera_device_id    : STRING    [required, system device identifier]
  camera_device_label : STRING    [required, human-readable camera name]
  target_software     : ENUM(foundry_vtt, roll20, dnd_beyond, fantasy_grounds,
                              owlbear_rodeo, discord, other)
                                  [required]
  dice_set_id         : UUID      [nullable, foreign key -> PersonalDiceSet.id]
  started_at          : DATETIME  [required, UTC, auto-generated on creation]
  ended_at            : DATETIME  [nullable, set when session is closed]
  roll_results        : RollResult[]
                                  [one-to-many, foreign key on RollResult.session_id]
}
```

### AppSettings
Singleton. Created on first run and updated in place thereafter.

```
AppSettings {
  id                             : INTEGER   [required, primary key, always 1]
  last_used_camera_device_id     : STRING    [nullable]
  last_used_camera_label         : STRING    [nullable]
  last_used_target_software      : ENUM(foundry_vtt, roll20, dnd_beyond, fantasy_grounds,
                                         owlbear_rodeo, discord, other)
                                             [nullable]
  installed_model_version        : STRING    [nullable, semantic version e.g. "1.4.2"]
  privacy_policy_accepted        : BOOLEAN   [required, default: false]
  privacy_policy_accepted_at     : DATETIME  [nullable, set when privacy_policy_accepted
                                              = true]
  updated_at                     : DATETIME  [required, UTC, updated on every write]
}
```

### PersonalDiceSet
Stored locally and synced to S3.

```
PersonalDiceSet {
  id           : UUID      [required, primary key, auto-generated]
  name         : STRING    [required, max: 100 chars, user-defined]
  die_profiles : DieProfile[]
                           [one-to-many, foreign key on DieProfile.dice_set_id]
  sync_status  : ENUM(local_only, synced, pending_sync)
                           [required, default: local_only]
  synced_at    : DATETIME  [nullable, set when sync_status = synced]
  created_at   : DATETIME  [required, UTC, auto-generated on creation]
  updated_at   : DATETIME  [required, UTC, updated on every write]
}
```

### DieProfile
Child of PersonalDiceSet. Represents training data captured for one die.

```
DieProfile {
  id               : UUID      [required, primary key, auto-generated]
  dice_set_id      : UUID      [required, foreign key -> PersonalDiceSet.id]
  die_type         : ENUM(d4, d6, d8, d10, d10_percentile, d12, d20, d100)
                               [required]
  training_images  : TrainingImage[]
                               [one-to-many, foreign key on TrainingImage.die_profile_id]
  created_at       : DATETIME  [required, UTC, auto-generated on creation]
  updated_at       : DATETIME  [required, UTC, updated on every write]

  NOTE: Minimum image count per die face to be confirmed with ML team before build.
}
```

### TrainingImage
Child of DieProfile. One record per captured image during dice set training.

```
TrainingImage {
  id             : UUID      [required, primary key, auto-generated]
  die_profile_id : UUID      [required, foreign key -> DieProfile.id]
  face_value     : INTEGER   [required, min: 1, the face shown in this image]
  image_data     : BLOB      [required, raw captured frame]
  captured_at    : DATETIME  [required, UTC, auto-generated on creation]
}
```

### Relationships

```
Session          1 ---> many  RollResult
RollResult       1 ---> 0..1  ErrorPackage
PersonalDiceSet  1 ---> many  DieProfile
DieProfile       1 ---> many  TrainingImage
Session          many -> 0..1 PersonalDiceSet
AppSettings      (singleton, no relationships)
```

Image blobs in `TrainingImage` and `ErrorPackage` may be stored as file references on disk rather than directly in SQLite. Both approaches are valid; the decision is left to the developer.

---

## Packaging and Deployment

**MVP (v1.0):**
- PyInstaller bundles Python, Flask, OpenCV, ONNX Runtime, and the Dice Link app into a single .exe (~100-150MB)
- Embedded ONNX model v1.0.0 included in installer
- User data and model updates stored in AppData directory
- Auto-update mechanism checks for new models on app launch
- Single-file executable; no runtime dependencies required

**Full Vision:**
- Same approach; scale to Mac and Linux platforms
- Optional account system added in v1.1+
- Personal dice set syncing to S3
- Continuous model improvement pipeline

---

## Open Items

The following are unresolved at the time of writing. See the Full Vision Specification for full detail.

- **Minimum training images per die face** — to be confirmed with the ML team before the personal dice set flow is built.
- **Integration interfaces** — exact communication contracts between the desktop app and browser extensions and any bots are to be defined in collaboration with parallel development teams. Foundry VTT integration is already defined via local WebSocket protocol.
- **GDPR and international compliance** — ICO registration in progress. No server-connected features should go live until compliance requirements are confirmed.
- **Account system** — planned for a future version. Developers should be aware it is coming but must not architect for it in MVP.
