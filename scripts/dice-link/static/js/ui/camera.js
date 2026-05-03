/**
 * Camera UI Module
 * Handles camera selection, live feed display via canvas, and tray region definition.
 */

let cameraActive = false;
let cameraSource = null; // 'usb' | null
let suppressSelectChange = false;
let motionPollInterval = null;

let cameraWS = null;
let cameraDisplayRAF = null;
let trayBbox = null;
let savedTrayBbox = null;
let usbFrameCanvas = null;
let usbFrameCtx = null;
let inTrayDefinitionMode = false;

function initCameraUI() {
    loadCameraList();
    loadTrayRegion();

    const cameraSelect = document.getElementById('camera-select');
    if (cameraSelect) {
        cameraSelect.addEventListener('change', async () => {
            if (suppressSelectChange) return;
            const index = parseInt(cameraSelect.value);
            await selectCamera(index);
        });
    }

    const canvas = document.getElementById('tray-canvas');
    if (canvas) canvas.addEventListener('click', onTrayCanvasClick);

    updateCameraButtons('off');
}

function updateCameraButtons(state) {
    const btns = document.querySelectorAll('.user-control-btn');
    if (btns.length < 4) return;

    btns.forEach(btn => {
        btn.textContent = '';
        btn.onclick = null;
    });

    if (state === 'phone') {
        btns[1].textContent = 'Refresh';
        btns[1].onclick = loadCameraList;
    } else if (state === 'off') {
        btns[0].textContent = 'Start';
        btns[0].onclick = toggleCamera;
        btns[1].textContent = 'Refresh';
        btns[1].onclick = loadCameraList;
    } else if (state === 'running') {
        btns[0].textContent = 'Stop';
        btns[0].onclick = toggleCamera;
        btns[1].textContent = 'Calibrate';
        btns[1].onclick = calibrateCamera;
        btns[3].textContent = 'Define Tray';
        btns[3].onclick = startTrayDefinition;
    } else if (state === 'define') {
        btns[0].textContent = 'Clear';
        btns[0].onclick = clearTrayPoints;
        btns[1].textContent = 'Confirm';
        btns[1].onclick = confirmTrayRegion;
        btns[2].textContent = 'Cancel';
        btns[2].onclick = exitTrayDefinition;
    }
}

async function calibrateCamera() {
    try {
        const response = await fetch('/api/camera/calibrate', { method: 'POST' });
        const data = await response.json();
        showCameraStatus(data.success ? 'Calibrated' : 'Failed — start camera first');
    } catch (error) {
        debugError('Failed to calibrate camera', error);
        showCameraStatus('Error');
    }
}

function showCameraStatus(message) {
    const status = document.getElementById('camera-status');
    if (!status) return;
    status.textContent = message;
    status.classList.add('visible');
    setTimeout(() => {
        status.classList.remove('visible');
        status.textContent = '';
    }, 2500);
}

async function loadCameraList() {
    suppressSelectChange = true;
    try {
        const response = await fetch('/api/cameras');
        const data = await response.json();
        const select = document.getElementById('camera-select');
        if (!select) return;

        select.innerHTML = '';
        if (data.cameras.length === 0) {
            select.innerHTML = '<option value="">No cameras found</option>';
            return;
        }

        data.cameras.forEach(cam => {
            const option = document.createElement('option');
            option.value = cam.index;
            option.textContent = cam.name;
            select.appendChild(option);
        });
        select.value = data.selectedIndex;
    } catch (error) {
        debugError('Failed to load camera list', error);
    } finally {
        suppressSelectChange = false;
    }
}

async function loadTrayRegion() {
    try {
        const response = await fetch('/api/camera/tray-region');
        const data = await response.json();
        if (data.points && data.points.length >= 3) {
            trayBbox = computeTrayBbox(data.points);
        }
    } catch (error) {
        debugError('Failed to load tray region', error);
    }
}

function computeTrayBbox(points) {
    const xs = points.map(p => p[0]);
    const ys = points.map(p => p[1]);
    return {
        x0: Math.min(...xs),
        y0: Math.min(...ys),
        x1: Math.max(...xs),
        y1: Math.max(...ys)
    };
}

async function selectCamera(index) {
    hidePhoneQRCode();

    try {
        await fetch('/api/camera/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index })
        });

        if (index === -1) {
            if (cameraActive) await stopCamera();
            showPhoneQRCode();
            return;
        }

        if (cameraActive) {
            await stopCamera();
            await startCamera();
        } else {
            updateCameraButtons('off');
        }
    } catch (error) {
        debugError('Failed to select camera', error);
    }
}

function showPhoneQRCode() {
    const container = document.getElementById('phone-qr-container');
    const img = document.getElementById('phone-qr-img');

    if (img) img.src = '/api/phone-camera/qr';
    if (container) container.classList.remove('hidden');

    updateCameraButtons('phone');
    showCameraStatus('Scan QR code to connect phone');
}

function hidePhoneQRCode() {
    const container = document.getElementById('phone-qr-container');
    if (container) container.classList.add('hidden');
}

function onPhoneCameraConnected() {
    hidePhoneQRCode();
    cameraActive = true;
    cameraSource = 'usb';
    const panel = document.querySelector('.camera-window-panel');
    if (panel) panel.classList.add('streaming');
    updateCameraButtons('running');
    startCameraWebSocket();
    startCameraDisplayLoop();
    startMotionPolling();
    showCameraStatus('Phone connected');
}

function onPhoneCameraDisconnected() {
    cameraSource = null;
    cameraActive = false;
    const panel = document.querySelector('.camera-window-panel');
    if (panel) panel.classList.remove('streaming');
    stopCameraWebSocket();
    stopCameraDisplayLoop();
    stopMotionPolling();
    showPhoneQRCode();
    showCameraStatus('Phone disconnected');
}

// ── USB Camera WebSocket ────────────────────────────────────────────────────

function startCameraWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws/camera`;
    cameraWS = new WebSocket(wsUrl);
    cameraWS.binaryType = 'arraybuffer';

    cameraWS.onmessage = (event) => {
        const view = new DataView(event.data);
        const w = view.getUint16(0, false);
        const h = view.getUint16(2, false);

        if (!usbFrameCanvas || usbFrameCanvas.width !== w || usbFrameCanvas.height !== h) {
            usbFrameCanvas = document.createElement('canvas');
            usbFrameCanvas.width = w;
            usbFrameCanvas.height = h;
            usbFrameCtx = usbFrameCanvas.getContext('2d');
        }

        const rgba = new Uint8ClampedArray(event.data, 4);
        usbFrameCtx.putImageData(new ImageData(rgba, w, h), 0, 0);
    };

    cameraWS.onclose = () => { cameraWS = null; };
    cameraWS.onerror = () => { cameraWS = null; };
}

function stopCameraWebSocket() {
    if (cameraWS) {
        cameraWS.close();
        cameraWS = null;
    }
    usbFrameCanvas = null;
    usbFrameCtx = null;
}

// ── Camera Display Loop ─────────────────────────────────────────────────────

function startCameraDisplayLoop() {
    if (cameraDisplayRAF) return;

    const canvas = document.getElementById('camera-display');
    if (!canvas) return;

    const parent = canvas.parentElement;
    canvas.width = parent ? parent.offsetWidth : 640;
    canvas.height = parent ? parent.offsetHeight : 480;
    canvas.style.display = 'block';

    const ctx = canvas.getContext('2d');

    function draw() {
        let source = null;
        let sourceW = 0;
        let sourceH = 0;

        if (cameraSource === 'usb') {
            if (usbFrameCanvas) {
                source = usbFrameCanvas;
                sourceW = usbFrameCanvas.width;
                sourceH = usbFrameCanvas.height;
            }
        }

        if (source && sourceW > 0 && sourceH > 0) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            if (trayBbox && !inTrayDefinitionMode) {
                const tw = (trayBbox.x1 - trayBbox.x0) * sourceW;
                const th = (trayBbox.y1 - trayBbox.y0) * sourceH;
                const cx = (trayBbox.x0 + trayBbox.x1) / 2 * sourceW;
                const cy = (trayBbox.y0 + trayBbox.y1) / 2 * sourceH;
                const scale = Math.min(canvas.width / tw, canvas.height / th);
                const dx = canvas.width / 2 - cx * scale;
                const dy = canvas.height / 2 - cy * scale;
                ctx.drawImage(source, 0, 0, sourceW, sourceH, dx, dy, sourceW * scale, sourceH * scale);
            } else {
                const scale = Math.min(canvas.width / sourceW, canvas.height / sourceH);
                const dw = sourceW * scale;
                const dh = sourceH * scale;
                const dx = (canvas.width - dw) / 2;
                const dy = (canvas.height - dh) / 2;
                ctx.drawImage(source, 0, 0, sourceW, sourceH, dx, dy, dw, dh);
            }
        } else {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }

        cameraDisplayRAF = requestAnimationFrame(draw);
    }

    cameraDisplayRAF = requestAnimationFrame(draw);
}

function stopCameraDisplayLoop() {
    if (cameraDisplayRAF) {
        cancelAnimationFrame(cameraDisplayRAF);
        cameraDisplayRAF = null;
    }
    const canvas = document.getElementById('camera-display');
    if (canvas) {
        canvas.style.display = 'none';
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

// ── Camera Start / Stop ─────────────────────────────────────────────────────

async function startCamera() {
    trayBbox = null;
    try {
        const response = await fetch('/api/camera/start', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            cameraActive = true;
            cameraSource = 'usb';
            const panel = document.querySelector('.camera-window-panel');
            if (panel) panel.classList.add('streaming');
            updateCameraButtons('running');
            startCameraWebSocket();
            startCameraDisplayLoop();
            startMotionPolling();
        }
    } catch (error) {
        debugError('Failed to start camera', error);
    }
}

async function stopCamera() {
    try {
        await fetch('/api/camera/stop', { method: 'POST' });
        cameraActive = false;
        cameraSource = null;
        const panel = document.querySelector('.camera-window-panel');
        if (panel) panel.classList.remove('streaming');
        stopCameraWebSocket();
        stopCameraDisplayLoop();
        stopMotionPolling();
        updateCameraButtons('off');
    } catch (error) {
        debugError('Failed to stop camera', error);
    }
}

async function toggleCamera() {
    if (cameraActive) {
        await stopCamera();
    } else {
        await startCamera();
    }
}

function startMotionPolling() {
    if (motionPollInterval) return;
    motionPollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/camera/motion');
            const data = await response.json();
            updateMotionLabel(data.motion);
        } catch (e) {}
    }, 300);
}

function stopMotionPolling() {
    if (motionPollInterval) {
        clearInterval(motionPollInterval);
        motionPollInterval = null;
    }
    const label = document.getElementById('camera-motion');
    if (label) {
        label.textContent = '';
        label.className = 'camera-motion';
    }
}

function updateMotionLabel(isMotion) {
    const label = document.getElementById('camera-motion');
    if (!label) return;
    label.textContent = isMotion ? 'Rolling' : 'Still';
    label.className = 'camera-motion ' + (isMotion ? 'rolling' : 'still');
}

// ── Tray region definition ──────────────────────────────────────────────────

let trayPoints = [];

function startTrayDefinition() {
    if (!cameraActive) {
        showCameraStatus('Start camera first');
        return;
    }

    trayPoints = [];
    savedTrayBbox = trayBbox;
    trayBbox = null;
    inTrayDefinitionMode = true;

    const canvas = document.getElementById('tray-canvas');
    if (canvas) {
        canvas.classList.add('define-mode');
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
    }

    document.getElementById('camera-controls-normal').classList.add('hidden');
    document.getElementById('camera-controls-define').classList.remove('hidden');
    updateCameraButtons('define');
}

function onTrayCanvasClick(e) {
    const canvas = document.getElementById('tray-canvas');
    if (!canvas || !canvas.classList.contains('define-mode')) return;
    if (!usbFrameCanvas || usbFrameCanvas.width === 0 || usbFrameCanvas.height === 0) return;

    const rect = canvas.getBoundingClientRect();
    const clickX = (e.clientX - rect.left) * (canvas.width / rect.width);
    const clickY = (e.clientY - rect.top) * (canvas.height / rect.height);

    const sourceW = usbFrameCanvas.width;
    const sourceH = usbFrameCanvas.height;
    const scale = Math.min(canvas.width / sourceW, canvas.height / sourceH);
    const dw = sourceW * scale;
    const dh = sourceH * scale;
    const dx = (canvas.width - dw) / 2;
    const dy = (canvas.height - dh) / 2;

    const fx = (clickX - dx) / dw;
    const fy = (clickY - dy) / dh;
    if (fx < 0 || fx > 1 || fy < 0 || fy > 1) return;

    trayPoints.push([fx, fy]);
    drawTrayPolygon();
}

function drawTrayPolygon() {
    const canvas = document.getElementById('tray-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (trayPoints.length === 0) return;
    if (!usbFrameCanvas || usbFrameCanvas.width === 0 || usbFrameCanvas.height === 0) return;

    const sourceW = usbFrameCanvas.width;
    const sourceH = usbFrameCanvas.height;
    const scale = Math.min(canvas.width / sourceW, canvas.height / sourceH);
    const dw = sourceW * scale;
    const dh = sourceH * scale;
    const dx = (canvas.width - dw) / 2;
    const dy = (canvas.height - dh) / 2;
    const toCanvas = pt => [dx + pt[0] * dw, dy + pt[1] * dh];

    ctx.beginPath();
    const [x0, y0] = toCanvas(trayPoints[0]);
    ctx.moveTo(x0, y0);
    for (let i = 1; i < trayPoints.length; i++) {
        const [x, y] = toCanvas(trayPoints[i]);
        ctx.lineTo(x, y);
    }
    if (trayPoints.length >= 3) ctx.closePath();
    ctx.strokeStyle = 'rgba(255, 215, 0, 0.85)';
    ctx.lineWidth = 2;
    ctx.stroke();

    trayPoints.forEach(pt => {
        const [x, y] = toCanvas(pt);
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#FFD700';
        ctx.fill();
    });
}

function clearTrayPoints() {
    trayPoints = [];
    const canvas = document.getElementById('tray-canvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

async function confirmTrayRegion() {
    if (trayPoints.length < 3) {
        showCameraStatus('Need at least 3 points');
        return;
    }

    try {
        const response = await fetch('/api/camera/tray-region', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ points: trayPoints })
        });
        const data = await response.json();
        if (data.success) {
            trayBbox = computeTrayBbox(trayPoints);
            savedTrayBbox = null;
            showCameraStatus('Tray saved');
        }
        exitTrayDefinition();
    } catch (error) {
        debugError('Failed to save tray region', error);
        exitTrayDefinition();
    }
}

function exitTrayDefinition() {
    inTrayDefinitionMode = false;
    if (savedTrayBbox !== null) {
        trayBbox = savedTrayBbox;
        savedTrayBbox = null;
    }

    const canvas = document.getElementById('tray-canvas');
    if (canvas) {
        canvas.classList.remove('define-mode');
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    document.getElementById('camera-controls-normal').classList.remove('hidden');
    document.getElementById('camera-controls-define').classList.add('hidden');
    updateCameraButtons('running');
}
