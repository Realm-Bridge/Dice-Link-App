# DLA Packaging and Deployment Specification

## Overview

This document outlines how DLA (Dice Link App) should be packaged for end users, including the ML model workflow, data collection strategy, and update system.

---

## 1. Packaging Method: PyInstaller

**Decision:** Use PyInstaller (not Electron or Nuitka)

**Rationale:**
- **Electron ruled out** - Bundles full Chromium browser (~150-300MB), slower startup, heavier memory footprint. For a dice detection app requiring fast camera response, this overhead is unacceptable.
- **Nuitka ruled out** - Compiles Python to C for faster execution, but adds complexity. The performance bottleneck is ML inference, not Python execution speed.
- **PyInstaller chosen** - Well-documented, widely used, sufficient for PyWebView + FastAPI apps, simpler build process.

---

## 2. ML Framework Strategy: Split Architecture

**Decision:** ONNX Runtime on user PCs, PyTorch/TensorFlow on servers

### User PC (DLA Application)
- Uses **ONNX Runtime** for inference only
- Lightweight, optimized for running predictions
- No training happens on user machines
- Works on CPU (no CUDA dependency)

### Realm Bridge Servers
- Uses **PyTorch or TensorFlow** for training
- Receives anonymized training data from users
- Retrains model periodically with new data
- Exports trained model to ONNX format for distribution

### Why This Split Works
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

## 3. GPU/CUDA Requirements: CPU-Only Initially

**Decision:** Ship CPU-only version first

**Rationale:**
- Simpler packaging (no CUDA dependencies)
- Works on all Windows/Mac PCs regardless of GPU
- Modern CPUs handle dice detection adequately
- Reduces bundle size significantly
- Can add optional GPU acceleration later if needed

**Future consideration:** If inference speed becomes an issue, offer a separate "GPU-accelerated" download with CUDA support.

---

## 4. Model File Handling: Hybrid Approach

**Decision:** Embedded initial model + automatic updates

### Initial Installation
- Base ONNX model embedded in the .exe/installer
- App works immediately offline
- No internet required for first run

### Model Storage Location
```
Windows: %APPDATA%/DiceLink/models/
Mac:     ~/Library/Application Support/DiceLink/models/
```

**Do NOT embed models inside .exe for updates** - store in AppData so they can be updated without reinstalling.

### Directory Structure
```
%APPDATA%/DiceLink/
├── models/
│   ├── dice_detector_v1.2.3.onnx    # Current model
│   └── model_version.json            # Version metadata
├── training_queue/
│   ├── session_2024_01_15_001.json  # Pending upload
│   └── session_2024_01_15_002.json  # Pending upload
├── config.json                       # User settings
└── logs/
    └── dla.log                       # Application logs
```

---

## 5. Data Collection Workflow

### Privacy Requirements
- **User consent required** - First-run dialog explaining data collection
- **Anonymized data** - No user identifiers attached to training data
- **Opt-out option** - Users can disable data collection in settings
- **Clear privacy policy** - Explain what data is collected and why

### Collection Process (During Session)
```python
# When dice are detected and confirmed by user
training_sample = {
    "timestamp": "2024-01-15T14:32:00Z",
    "image": base64_encoded_cropped_dice_image,
    "detected_value": 15,
    "confirmed_value": 15,  # What user confirmed (may differ)
    "dice_type": "d20",
    "lighting_conditions": "indoor",  # Optional metadata
    "camera_id": "hashed_camera_identifier"
}

# Store locally - DO NOT upload during session
save_to_training_queue(training_sample)
```

### Upload Process (On App Close)
```python
def on_app_closing():
    if user_has_consented_to_data_collection():
        pending_files = get_training_queue_files()
        
        for file in pending_files:
            success = upload_to_realm_bridge_server(file)
            if success:
                delete_local_file(file)
            # If upload fails, file remains for next attempt
```

### Upload Process (On App Open)
```python
def on_app_starting():
    # First: Complete any pending uploads from last session
    if user_has_consented_to_data_collection():
        upload_pending_training_data()
    
    # Second: Check for model updates
    check_and_download_model_updates()
```

---

## 6. Model Update System

### Version Checking
```python
def check_and_download_model_updates():
    local_version = read_local_model_version()  # e.g., "1.2.3"
    
    try:
        server_response = requests.get(
            "https://api.realmbridge.com/dla/model/latest",
            timeout=5
        )
        server_version = server_response.json()["version"]
        download_url = server_response.json()["download_url"]
        
        if version_is_newer(server_version, local_version):
            download_new_model(download_url, server_version)
            
    except ConnectionError:
        # Offline - use existing model, try again next startup
        log("Could not check for updates - using existing model")
```

### Server API Endpoints (for your backend team)
```
GET  /dla/model/latest
     Returns: { "version": "1.2.4", "download_url": "...", "size_bytes": 45000000 }

GET  /dla/model/download/{version}
     Returns: ONNX model file

POST /dla/training/upload
     Body: { samples: [...training data...] }
     Returns: { "received": true, "sample_count": 15 }
```

### Update Frequency
- **Model updates:** Check on every app startup (quick version check)
- **Model retraining:** Server-side, approximately weekly based on new data volume
- **Forced updates:** Server can flag minimum required version for compatibility

---

## 7. Installer vs Portable

**Decision:** Installer (.msi) for primary distribution

**Rationale:**
- Auto-update functionality requires persistent storage location
- AppData storage for models and training queue
- Can register file associations if needed
- Cleaner uninstall experience
- Start menu shortcuts

**Also provide:** Portable .exe option for users who prefer it (with note that auto-updates won't work as smoothly)

---

## 8. Bundle Contents

### Included in Installer
```
DiceLink/
├── DiceLink.exe              # Main application
├── python39.dll              # Python runtime (bundled by PyInstaller)
├── onnxruntime.dll           # ONNX inference engine
├── opencv_*.dll              # OpenCV for camera
├── models/
│   └── dice_detector_v1.0.0.onnx  # Initial model
├── static/
│   ├── js/                   # Frontend JavaScript
│   ├── css/                  # Styles
│   └── DLC Dice/             # SVG dice assets
└── templates/
    └── index.html            # Main UI
```

### Estimated Sizes
- Python runtime + dependencies: ~50-80MB
- ONNX Runtime (CPU): ~15-20MB
- OpenCV: ~20-30MB
- Initial model: ~10-50MB (depends on architecture)
- Static assets: ~5MB
- **Total installer: ~100-150MB**

---

## 9. UI Polish Requirements

The frontend must match DLC's design language:

### Color Palette
```css
:root {
  --dlc-bg-dark: #212a37;
  --dlc-bg-section: #2a3547;
  --dlc-bg-input: #181f2b;
  --dlc-border: #6f2e9a;
  --dlc-accent: #6f2e9a;
  --dlc-accent-pink: #a78bfa;
  --dlc-text-primary: #e7f6ff;
  --dlc-text-secondary: #a0a0b0;
}
```

### Design Requirements
- Clean, modern dark theme
- Consistent with DLC (Foundry module) styling
- Responsive layout within window
- Smooth transitions between Roll Window states
- Professional appearance suitable for paid product

---

## 10. Implementation Priority

### Phase 1: Core Packaging
1. Set up PyInstaller build script
2. Create AppData directory structure on first run
3. Bundle initial ONNX model
4. Test on clean Windows machine

### Phase 2: Update System
1. Implement version checking on startup
2. Background model download
3. Graceful fallback when offline

### Phase 3: Data Collection
1. First-run consent dialog
2. Local training data storage
3. Upload on app close
4. Upload pending data on app open

### Phase 4: Installer
1. Create .msi installer
2. Start menu integration
3. Uninstaller
4. Optional: Auto-update mechanism

---

## Questions for ML Specialist

When your ML specialist joins, confirm:

1. **Model architecture** - What size will the trained ONNX model be?
2. **Input format** - What image preprocessing does the model expect?
3. **Output format** - Bounding boxes + class labels? Just class labels?
4. **Training data format** - What metadata should we collect with each image?
5. **Minimum samples** - How many samples needed before retraining improves results?
