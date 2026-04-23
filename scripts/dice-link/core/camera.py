"""Camera management for Dice Link - Phase 3"""

import cv2
import base64
import threading
import time
from typing import Optional
from debug import log


class CameraManager:
    """Manages camera access, capture, and streaming"""
    
    def __init__(self):
        self.camera: Optional[cv2.VideoCapture] = None
        self.camera_index: int = 0
        self.is_capturing: bool = False
        self.current_frame: Optional[bytes] = None
        self.frame_lock = threading.Lock()
        self.capture_thread: Optional[threading.Thread] = None
        self.target_fps: int = 15
        self._stop_event = threading.Event()
    
    def list_cameras(self) -> list:
        """
        Return list of available camera devices.
        Returns: List of dicts with {index, name}
        """
        log("Camera", "Enumerating cameras using DirectShow backend...")
        cameras = []
        
        # Try to detect cameras (check indices 0-5)
        # Use CAP_DSHOW (DirectShow) on Windows for better compatibility
        for i in range(6):
            log("Camera", f"Testing camera index {i}...")
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            
            # Set buffer size to 1
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if cap.isOpened():
                log("Camera", f"Camera {i} opened successfully!")
                
                # Try to read one frame to verify it works
                ret, frame = cap.read()
                if ret and frame is not None:
                    log("Camera", f"Camera {i} is readable (frame size: {frame.shape})")
                    cameras.append({
                        "index": i,
                        "name": f"Camera {i}"
                    })
                else:
                    log("Camera", f"Camera {i} opened but cannot read frames")
                cap.release()
            else:
                log("Camera", f"Camera {i} cannot be opened")
        
        log("Camera", f"Found {len(cameras)} usable cameras: {cameras}")
        return cameras
    
    def select_camera(self, index: int) -> bool:
        """Select a specific camera by index"""
        log("Camera", f"Selecting camera index {index}")
        
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
        
        # Use DirectShow backend on Windows for better reliability
        self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.camera.isOpened():
            return False
        
        # Set camera properties for better performance
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, fps)
        
        self.target_fps = fps
        self.is_capturing = True
        self._stop_event.clear()
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        return True
    
    def _capture_loop(self):
        """Background thread that continuously captures frames"""
        frame_interval = 1.0 / self.target_fps
        
        while not self._stop_event.is_set() and self.camera and self.camera.isOpened():
            start_time = time.time()
            
            ret, frame = self.camera.read()
            if ret:
                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                with self.frame_lock:
                    self.current_frame = buffer.tobytes()
            
            # Maintain target FPS
            elapsed = time.time() - start_time
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def stop_capture(self):
        """Stop capturing and release camera"""
        self._stop_event.set()
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        
        if self.camera:
            self.camera.release()
            self.camera = None
        
        self.is_capturing = False
        
        with self.frame_lock:
            self.current_frame = None
    
    def get_frame(self) -> Optional[str]:
        """
        Get current frame as base64-encoded JPEG data URI.
        Returns None if no frame available.
        """
        with self.frame_lock:
            if self.current_frame is None:
                return None
            
            b64_frame = base64.b64encode(self.current_frame).decode('utf-8')
            return f"data:image/jpeg;base64,{b64_frame}"
    
    def get_frame_dimensions(self) -> tuple:
        """Return (width, height) of current camera"""
        if self.camera and self.camera.isOpened():
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (width, height)
        return (640, 480)  # Default dimensions
    
    def capture_single_frame(self) -> Optional[str]:
        """Capture a single frame from the camera and return as data URI"""
        try:
            log("Camera", f"Capturing single frame from camera {self.camera_index}")
            
            # Create a new VideoCapture for this operation
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            log("Camera", f"VideoCapture created with DirectShow for index {self.camera_index}")
            
            if not cap.isOpened():
                log("Camera", f"ERROR: Failed to open camera {self.camera_index}")
                return None
            
            log("Camera", f"Camera opened successfully")
            
            # Set properties
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            log("Camera", f"Warming up camera...")
            for i in range(5):
                ret, frame = cap.read()
                log("Camera", f"Warmup {i+1}/5: ret={ret}, frame={'valid' if frame is not None else 'None'}")
            
            log("Camera", f"Reading final frame...")
            ret, frame = cap.read()
            
            if not ret:
                log("Camera", f"ERROR: read() returned False")
                cap.release()
                return None
            
            if frame is None:
                log("Camera", f"ERROR: frame is None")
                cap.release()
                return None
            
            log("Camera", f"Frame shape: {frame.shape}")
            
            # Encode to JPEG
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not success:
                log("Camera", f"ERROR: imencode failed")
                cap.release()
                return None
            
            log("Camera", f"Encoded successfully, buffer size: {len(buffer)}")
            
            # Convert to base64 data URI
            result = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
            log("Camera", f"Data URI created, length: {len(result)}")
            
            cap.release()
            log("Camera", f"Camera released")
            return result
            
        except Exception as e:
            log("Camera", f"EXCEPTION in capture_single_frame: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


# Global camera manager instance
camera_manager = CameraManager()
