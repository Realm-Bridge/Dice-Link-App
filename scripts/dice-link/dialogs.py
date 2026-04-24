from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from vtt_validator import VTTValidator


class ConnectionDialog(QDialog):
    """Dialog for entering and validating VTT server URL"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to VTT Server")
        self.setMinimumWidth(400)
        self.vtt_url = None
        self.is_validating = False
        
        # Create layout
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Enter VTT Server URL:")
        layout.addWidget(label)
        
        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://localhost:30000 or https://example.com")
        layout.addWidget(self.url_input)
        
        # Error message label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #ff6b6b;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.on_connect)
        button_layout.addWidget(self.connect_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def on_connect(self):
        """Handle connect button click - validate the URL"""
        url = self.url_input.text().strip()
        
        if not url:
            self.show_error("Please enter a URL")
            return
        
        # Store the URL being validated
        self.validating_url = url
        
        # Update UI state
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Validating...")
        self.error_label.setVisible(False)
        
        # Validate URL (synchronous - callback called directly)
        VTTValidator.validate_url(url, self.on_validation_complete)
    
    def on_validation_complete(self, is_valid, message, data):
        """Handle validation result"""
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        
        if is_valid:
            self.vtt_url = self.validating_url
            self.accept()
        else:
            self.show_error(message)
    
    def show_error(self, message):
        """Display error message"""
        self.error_label.setText(f"Error: {message}")
        self.error_label.setVisible(True)
