"""Camera management for Dice Link"""

import cv2
import base64
import struct
import threading
import time
import numpy as np
from typing import Optional
from pathlib import Path
from debug import log
from core.storage import get_appdata_path

PHONE_CAMERA_INDEX = -1


class CameraManager:
    """Manages camera access, capture, and streaming"""

    def __init__(self):
        self.camera: Optional[cv2.VideoCapture] = None
        self.camera_index: int = 0
        self.is_capturing: bool = False
        self.phone_camera_mode: bool = False
        self.current_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()
        self.capture_thread: Optional[threading.Thread] = None
        self.target_fps: int = 15
        self._stop_event = threading.Event()
        self.tray_polygon: list = []
        self._prev_motion_frame: Optional[np.ndarray] = None
        self._motion_detected: bool = False
        self._still_counter: int = 0
        self._motion_onset_time: Optional[float] = None
        self._load_tray_region()

    @property
    def is_motion(self) -> bool:
        return self._motion_detected

    def _check_motion(self, frame: np.ndarray):
        """Compare current frame to previous to detect movement in the tray."""
        if self._prev_motion_frame is None or self._prev_motion_frame.shape != frame.shape:
            self._prev_motion_frame = frame.copy()
            return

        diff = cv2.absdiff(frame, self._prev_motion_frame)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(diff_gray, 25, 255, cv2.THRESH_BINARY)

        if self.tray_polygon and len(self.tray_polygon) >= 3:
            h, w = frame.shape[:2]
            pts = np.array(
                [[int(p[0] * w), int(p[1] * h)] for p in self.tray_polygon],
                dtype=np.int32
            )
            tray_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(tray_mask, [pts], 255)
            thresh = cv2.bitwise_and(thresh, tray_mask)

        changed_pixels = cv2.countNonZero(thresh)

        h, w = frame.shape[:2]
        motion_threshold = max(500, int(h * w * 0.0015))

        if changed_pixels > motion_threshold:
            self._still_counter = 0
            if self._motion_onset_time is None:
                self._motion_onset_time = time.time()
            elif time.time() - self._motion_onset_time >= 0.25:
                self._motion_detected = True
        else:
            self._still_counter += 1
            self._motion_onset_time = None
            if self._still_counter > 15:
                self._motion_detected = False

        self._prev_motion_frame = frame.copy()

    def _tray_region_path(self) -> Path:
        return get_appdata_path() / 'tray_region.json'

    def _load_tray_region(self):
        """Load saved tray polygon from disk if it exists."""
        import json
        path = self._tray_region_path()
        if path.exists():
            with open(str(path)) as f:
                self.tray_polygon = json.load(f)
            log("Camera", f"Tray region loaded ({len(self.tray_polygon)} points)")

    def set_tray_region(self, points: list) -> bool:
        """Save normalised polygon points as the tray region."""
        import json
        if len(points) < 3:
            return False
        self.tray_polygon = points
        path = self._tray_region_path()
        with open(str(path), 'w') as f:
            json.dump(points, f)
        log("Camera", f"Tray region saved ({len(points)} points)")
        return True

    def list_cameras(self) -> list:
        """
        Return list of available camera devices.
        Returns: List of dicts with {index, name}
        """
        log("Camera", "Enumerating cameras using DirectShow backend...")
        cameras = []

        for i in range(6):
            log("Camera", f"Testing camera index {i}...")
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    log("Camera", f"Camera {i} is readable (frame size: {frame.shape})")
                    cameras.append({"index": i, "name": f"Camera {i}"})
                else:
                    log("Camera", f"Camera {i} opened but cannot read frames")
                cap.release()
            else:
                log("Camera", f"Camera {i} cannot be opened")

        cameras.append({"index": PHONE_CAMERA_INDEX, "name": "Phone Camera"})
        log("Camera", f"Found {len(cameras) - 1} USB cameras + Phone Camera option")
        return cameras

    def select_camera(self, index: int) -> bool:
        """Select a specific camera by index"""
        log("Camera", f"Selecting camera index {index}")

        if index == PHONE_CAMERA_INDEX:
            self.camera_index = PHONE_CAMERA_INDEX
            log("Camera", "Phone Camera selected")
            return True

        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if cap.isOpened():
            cap.release()
            self.camera_index = index
            log("Camera", f"Successfully selected camera {index}")
            return True
        else:
            log("Camera", f"Failed to select camera {index}")
        return False

    def start_capture(self, fps: int = 15) -> bool:
        """
        Open selected camera and begin capturing frames.
        Returns True if capture started successfully.
        """
        if self.is_capturing:
            return True

        if self.camera_index == PHONE_CAMERA_INDEX:
            self.phone_camera_mode = True
            self.is_capturing = True
            self.target_fps = fps
            self._stop_event.clear()
            log("Camera", "Phone camera mode started — waiting for WebRTC frames")
            return True

        self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.camera.isOpened():
            return False

        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, fps)

        self.target_fps = fps
        self.is_capturing = True
        self._stop_event.clear()

        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        return True

    def _capture_loop(self):
        """Background thread that continuously captures frames from USB camera"""
        frame_interval = 1.0 / self.target_fps

        while not self._stop_event.is_set() and self.camera and self.camera.isOpened():
            start_time = time.time()

            ret, frame = self.camera.read()
            if ret:
                self._check_motion(frame)
                with self.frame_lock:
                    self.current_frame = frame

            elapsed = time.time() - start_time
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def receive_phone_frame(self, frame_bgr: np.ndarray):
        """Store a decoded video frame received from the phone via WebRTC."""
        self._check_motion(frame_bgr)
        with self.frame_lock:
            self.current_frame = frame_bgr

    def stop_capture(self):
        """Stop capturing and release camera"""
        self._motion_detected = False
        self._still_counter = 0
        self._motion_onset_time = None
        self._prev_motion_frame = None
        self.phone_camera_mode = False
        self._stop_event.set()

        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)

        if self.camera:
            self.camera.release()
            self.camera = None

        self.is_capturing = False

        with self.frame_lock:
            self.current_frame = None

    def get_processed_frame(self) -> Optional[bytes]:
        """Crop the tray region and return raw RGBA bytes prefixed with a 4-byte (width, height) header.
        Everything outside the tray polygon is transparent (alpha=0)."""
        if not self.is_capturing:
            return None

        with self.frame_lock:
            if self.current_frame is None:
                return None
            frame = self.current_frame.copy()

        if not self.tray_polygon or len(self.tray_polygon) < 3:
            log("Camera", "get_processed_frame: no tray polygon defined")
            return None

        h, w = frame.shape[:2]
        pts = np.array(
            [[int(p[0] * w), int(p[1] * h)] for p in self.tray_polygon],
            dtype=np.int32
        )

        x, y, bw, bh = cv2.boundingRect(pts)
        x = max(0, x)
        y = max(0, y)
        bw = min(bw, w - x)
        bh = min(bh, h - y)

        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)

        bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        bgra[:, :, 3] = mask
        crop = bgra[y:y + bh, x:x + bw]

        rgba_crop = cv2.cvtColor(crop, cv2.COLOR_BGRA2RGBA)
        return struct.pack('>HH', bw, bh) + rgba_crop.tobytes()

    def get_boundary_frame(self) -> Optional[bytes]:
        """Return the current frame with the tray boundary polygon drawn on it, as PNG bytes."""
        with self.frame_lock:
            if self.current_frame is None:
                return None
            frame = self.current_frame.copy()

        if not self.tray_polygon or len(self.tray_polygon) < 3:
            return None

        h, w = frame.shape[:2]
        pts = np.array(
            [[int(p[0] * w), int(p[1] * h)] for p in self.tray_polygon],
            dtype=np.int32
        )
        cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=3)

        _, buffer = cv2.imencode('.png', frame)
        return buffer.tobytes()

    def get_raw_rgba_bytes(self, max_height: int = None) -> Optional[bytes]:
        """Return current frame as raw RGBA bytes prefixed with 4-byte width/height header."""
        with self.frame_lock:
            if self.current_frame is None:
                return None
            frame = self.current_frame.copy()
        if max_height and frame.shape[0] > max_height:
            scale = max_height / frame.shape[0]
            new_w = int(frame.shape[1] * scale)
            frame = cv2.resize(frame, (new_w, max_height))
        frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        h, w = frame_rgba.shape[:2]
        header = struct.pack('>HH', w, h)
        return header + frame_rgba.tobytes()

    def get_frame(self) -> Optional[str]:
        """
        Get current frame as base64-encoded PNG data URI.
        Returns None if no frame available.
        """
        with self.frame_lock:
            if self.current_frame is None:
                return None
            frame = self.current_frame.copy()
        _, buffer = cv2.imencode('.png', frame)
        b64_frame = base64.b64encode(buffer.tobytes()).decode('utf-8')
        return f"data:image/png;base64,{b64_frame}"

    def get_frame_dimensions(self) -> tuple:
        """Return (width, height) of current camera"""
        if self.camera and self.camera.isOpened():
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (width, height)
        return (640, 480)

    def capture_single_frame(self) -> Optional[str]:
        """Capture a single frame from the camera and return as PNG data URI"""
        try:
            log("Camera", f"Capturing single frame from camera {self.camera_index}")

            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            log("Camera", f"VideoCapture created with DirectShow for index {self.camera_index}")

            if not cap.isOpened():
                log("Camera", f"ERROR: Failed to open camera {self.camera_index}")
                return None

            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            for i in range(5):
                ret, frame = cap.read()
                log("Camera", f"Warmup {i+1}/5: ret={ret}")

            ret, frame = cap.read()

            if not ret or frame is None:
                cap.release()
                return None

            log("Camera", f"Frame shape: {frame.shape}")

            success, buffer = cv2.imencode('.png', frame)
            if not success:
                cap.release()
                return None

            result = "data:image/png;base64," + base64.b64encode(buffer).decode('utf-8')
            cap.release()
            return result

        except Exception as e:
            log("Camera", f"EXCEPTION in capture_single_frame: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


# Global camera manager instance
camera_manager = CameraManager()
