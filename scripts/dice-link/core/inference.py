"""
ML Inference Module (ONNX Runtime)

This module handles loading and running ONNX models for dice detection.
Phase 2: Will integrate ONNX Runtime for CPU inference.
"""

import logging

logger = logging.getLogger(__name__)


class DiceInferenceEngine:
    """
    Loads ONNX model and performs dice detection inference.
    
    Future implementation:
    - Load .onnx model from models/ directory
    - Pre-process camera frame (resize, normalize)
    - Run inference on frame
    - Post-process detections (NMS, confidence threshold)
    - Return detected dice faces and positions
    """
    
    def __init__(self, model_path=None):
        """
        Initialize inference engine.
        
        Args:
            model_path (str): Path to .onnx model file
        """
        self.model_path = model_path
        self.session = None
        logger.info("DiceInferenceEngine initialized (stub)")
    
    def load_model(self, model_path):
        """Load ONNX model from disk."""
        # TODO: Implement ONNX Runtime session creation
        logger.info(f"Load model: {model_path}")
        pass
    
    def detect_dice(self, frame):
        """
        Run inference on a camera frame.
        
        Args:
            frame (numpy.ndarray): Camera frame (BGR format)
            
        Returns:
            list: Detected dice with format:
                [{'type': 'd20', 'value': 15, 'confidence': 0.95}, ...]
        """
        # TODO: Implement inference pipeline
        logger.debug("Detect dice called (stub)")
        return []
    
    def unload_model(self):
        """Release model resources."""
        # TODO: Clean up ONNX session
        logger.info("Unload model")
        pass


# Module-level instance (singleton pattern)
inference_engine = DiceInferenceEngine()


def detect_dice_from_frame(frame):
    """
    Convenience function for dice detection.
    
    Args:
        frame (numpy.ndarray): Camera frame
        
    Returns:
        list: Detected dice
    """
    return inference_engine.detect_dice(frame)
