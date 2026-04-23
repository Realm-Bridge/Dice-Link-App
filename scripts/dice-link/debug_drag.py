"""
Debug script for analyzing window drag juddering at high DPI scales.
This captures mouse position changes and logs them to identify rounding errors.

Usage:
1. Run this script alongside main.py
2. Drag the DLA window while monitoring output
3. Look for inconsistencies in coordinate deltas
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QColor, QPainter

class DragDebugOverlay(QWidget):
    """Overlay window that monitors and logs drag events"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drag Debug Monitor")
        self.resize(600, 400)
        self.setStyleSheet("background-color: black; color: white;")
        
        # Log storage
        self.logs = []
        self.last_pos = None
        self.dragging = False
        
        # Statistics
        self.delta_x_values = []
        self.delta_y_values = []
        
    def log(self, message):
        """Add log message and print to console"""
        self.logs.append(message)
        if len(self.logs) > 100:  # Keep last 100 messages
            self.logs.pop(0)
        print(message)
        self.update()
    
    def mousePressEvent(self, event):
        """Start tracking"""
        self.dragging = True
        self.last_pos = event.globalPosition().toPoint()
        self.log(f"[DRAG START] Position: {self.last_pos.x()}, {self.last_pos.y()}")
        self.delta_x_values.clear()
        self.delta_y_values.clear()
    
    def mouseMoveEvent(self, event):
        """Log coordinate changes during drag"""
        if self.dragging and self.last_pos:
            current_pos = event.globalPosition().toPoint()
            delta_x = current_pos.x() - self.last_pos.x()
            delta_y = current_pos.y() - self.last_pos.y()
            
            self.delta_x_values.append(delta_x)
            self.delta_y_values.append(delta_y)
            
            # Only log every 5th movement to avoid spam
            if len(self.delta_x_values) % 5 == 0:
                avg_delta_x = sum(self.delta_x_values[-5:]) / 5
                avg_delta_y = sum(self.delta_y_values[-5:]) / 5
                self.log(f"[DRAG MOVE] Current: ({current_pos.x()}, {current_pos.y()}) Delta: ({delta_x}, {delta_y}) Avg5: ({avg_delta_x:.1f}, {avg_delta_y:.1f})")
            
            self.last_pos = current_pos
    
    def mouseReleaseEvent(self, event):
        """End tracking"""
        self.dragging = False
        if self.delta_x_values:
            avg_x = sum(self.delta_x_values) / len(self.delta_x_values)
            avg_y = sum(self.delta_y_values) / len(self.delta_y_values)
            std_x = (sum((x - avg_x)**2 for x in self.delta_x_values) / len(self.delta_x_values))**0.5
            std_y = (sum((y - avg_y)**2 for y in self.delta_y_values) / len(self.delta_y_values))**0.5
            
            self.log(f"[DRAG END] Movements: {len(self.delta_x_values)}")
            self.log(f"[DRAG END] X - Avg: {avg_x:.2f}, StdDev: {std_x:.2f} (judder indicator)")
            self.log(f"[DRAG END] Y - Avg: {avg_y:.2f}, StdDev: {std_y:.2f} (judder indicator)")
            self.log(f"[DRAG END] High StdDev = juddering (inconsistent deltas)")
    
    def paintEvent(self, event):
        """Draw logs on screen"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        painter.setPen(QColor(0, 255, 0))
        
        y = 20
        for log in self.logs[-20:]:  # Show last 20 logs
            painter.drawText(10, y, log)
            y += 20

if __name__ == "__main__":
    app = QApplication(sys.argv)
    debug_window = DragDebugOverlay()
    debug_window.show()
    sys.exit(app.exec())
