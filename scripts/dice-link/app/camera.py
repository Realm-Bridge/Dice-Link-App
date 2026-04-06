"""Camera management for Dice Link - Phase 3"""

import cv2
import base64
import threading
import time
from typing import Optional


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
        print(f"[Camera] Enumerating cameras...")
        cameras = []
        
        # Try to detect cameras (check indices 0-5)
        for i in range(6):
            print(f"[Camera] Testing camera index {i}...")
            cap = cv2.VideoCapture(i)
            
            # Set buffer size to 1 and disable backend warnings
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if cap.isOpened():
                print(f"[Camera] Camera {i} opened successfully!")
                
                # Try to read one frame to verify it works
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"[Camera] Camera {i} is readable (frame size: {frame.shape})")
                    cameras.append({
                        "index": i,
                        "name": f"Camera {i}"
                    })
                else:
                    print(f"[Camera] Camera {i} opened but cannot read frames")
                
                cap.release()
            else:
                print(f"[Camera] Camera {i} cannot be opened")
        
        print(f"[Camera] Found {len(cameras)} usable cameras: {cameras}")
        return cameras
    
    def select_camera(self, index: int) -> bool:
        """
        Select camera by index.
        Returns True if camera was selected successfully.
        """
        print(f"[Camera] Selecting camera index {index}")
        
        # Stop any current capture
        self.stop_capture()
        
        # Try to open the new camera
        test_cap = cv2.VideoCapture(index)
        if test_cap.isOpened():
            test_cap.release()
            self.camera_index = index
            print(f"[Camera] Successfully selected camera {index}")
            return True
        
        print(f"[Camera] Failed to select camera {index}")
        return False
    
    def start_capture(self, fps: int = 15) -> bool:
        """
        Open selected camera and begin capturing frames.
        Returns True if capture started successfully.
        """
        if self.is_capturing:
            return True
        
        self.camera = cv2.VideoCapture(self.camera_index)
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
        """
        Capture a single frame without starting continuous capture.
        Useful for camera preview in settings.
        Returns base64 data URI or None.
        """
        print(f"[Camera] Capturing single frame from camera {self.camera_index}")
        
        try:
            cap = cv2.VideoCapture(self.camera_index)
            print(f"[Camera] VideoCapture created for index {self.camera_index}")
            
            if not cap.isOpened():
                print(f"[Camera] ERROR: Failed to open camera {self.camera_index}")
                cap.release()
                return None
            
            print(f"[Camera] Camera opened successfully")
            
            # Set properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer to get fresh frames
            
            # Capture a few frames to let camera adjust
            print(f"[Camera] Warming up camera...")
            for i in range(5):
                ret, frame = cap.read()
                print(f"[Camera] Warmup {i+1}/5: ret={ret}, frame={'valid' if frame is not None else 'None'}")
            
            print(f"[Camera] Reading final frame...")
            ret, frame = cap.read()
            
            if not ret:
                print(f"[Camera] ERROR: read() returned False")
                cap.release()
                return None
            
            if frame is None:
                print(f"[Camera] ERROR: frame is None")
                cap.release()
                return None
            
            print(f"[Camera] Frame shape: {frame.shape}")
            
            # Encode as JPEG
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            if not success:
                print(f"[Camera] ERROR: imencode failed")
                cap.release()
                return None
            
            print(f"[Camera] Encoded successfully, buffer size: {len(buffer)}")
            
            b64_frame = base64.b64encode(buffer.tobytes()).decode('utf-8')
            result = f"data:image/jpeg;base64,{b64_frame}"
            
            print(f"[Camera] Data URI created, length: {len(result)}")
            cap.release()
            print(f"[Camera] Camera released")
            
            return result
        
        except Exception as e:
            print(f"[Camera] EXCEPTION in capture_single_frame: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


# Global camera manager instance
camera_manager = CameraManager()
