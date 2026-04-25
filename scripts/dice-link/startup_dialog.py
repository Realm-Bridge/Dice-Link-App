"""
Realm Bridge / Dice Link - Startup Dialog Module
Initial login and VTT selection dialog shown on application startup
Uses native PyQt6 widgets with the reusable CustomWindow/CustomTitleBar.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import pyqtSignal, Qt
from pathlib import Path

from custom_window import CustomWindow, COLOR_BG, COLOR_PURPLE, COLOR_TEXT

# Resolve the directory of this file
DICE_LINK_DIR = Path(__file__).resolve().parent


class StartupDialog(CustomWindow):
    """
    Initial login dialog shown on application startup.
    Uses native PyQt6 widgets with the reusable CustomWindow base class.
    """
    
    # Signal emitted when user successfully connects
    connect_successful = pyqtSignal(str, str, str)  # vtt_type, vtt_address, username
    
    def __init__(self):
        super().__init__(show_maximize=False, resizable=False, title="Dice Link Login")
        
        self.login_successful = False
        self.setFixedSize(550, 600)
        
        # Build the login form UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the login form UI."""
        # Content container
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLOR_BG};")
        self.content_layout.addWidget(content)
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(16)
        
        # Logo and title section
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        # Logo
        logo_label = QLabel()
        logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            scaled = pixmap.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled)
        header_layout.addWidget(logo_label)
        
        # Title
        title_label = QLabel("Dice Link Login")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT};
                font-size: 24px;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Separator
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {COLOR_PURPLE};")
        layout.addWidget(separator)
        
        layout.addSpacing(10)
        
        # Form fields
        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)
        
        # Connect me to (dropdown)
        row1 = QHBoxLayout()
        label1 = QLabel("Connect me to:")
        label1.setFixedWidth(120)
        label1.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 14px;")
        self.vtt_combo = QComboBox()
        self.vtt_combo.addItem("Foundry VTT")
        self.vtt_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #1a1f26;
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_PURPLE};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLOR_PURPLE};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1a1f26;
                color: {COLOR_TEXT};
                selection-background-color: {COLOR_PURPLE};
                border: 1px solid {COLOR_PURPLE};
            }}
        """)
        row1.addWidget(label1)
        row1.addWidget(self.vtt_combo, 1)
        form_layout.addLayout(row1)
        
        # VTT Address
        row2 = QHBoxLayout()
        label2 = QLabel("VTT Address:")
        label2.setFixedWidth(120)
        label2.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 14px;")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("http://localhost:30000 or https://example.com")
        self.address_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #1a1f26;
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_PURPLE};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit::placeholder {{
                color: #6b7280;
            }}
        """)
        row2.addWidget(label2)
        row2.addWidget(self.address_input, 1)
        form_layout.addLayout(row2)
        
        # User Name
        row3 = QHBoxLayout()
        label3 = QLabel("User Name:")
        label3.setFixedWidth(120)
        label3.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 14px;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Usually Email")
        self.username_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #1a1f26;
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_PURPLE};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit::placeholder {{
                color: #6b7280;
            }}
        """)
        row3.addWidget(label3)
        row3.addWidget(self.username_input, 1)
        form_layout.addLayout(row3)
        
        # Password
        row4 = QHBoxLayout()
        label4 = QLabel("Password:")
        label4.setFixedWidth(120)
        label4.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 14px;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #1a1f26;
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_PURPLE};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }}
        """)
        row4.addWidget(label4)
        row4.addWidget(self.password_input, 1)
        form_layout.addLayout(row4)
        
        layout.addLayout(form_layout)
        
        layout.addStretch()
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PURPLE};
                color: {COLOR_TEXT};
                border: none;
                border-radius: 4px;
                padding: 12px 40px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #7c3aed;
            }}
        """)
        self.connect_btn.clicked.connect(self._on_connect)
        layout.addWidget(self.connect_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        
        # Footer
        footer_layout = QHBoxLayout()
        
        # Create Free Account link
        create_account = QLabel('<a href="https://realmbridge.co.uk/" style="color: #6f2e9a;">Create Free Account</a>')
        create_account.setOpenExternalLinks(True)
        create_account.setStyleSheet("font-size: 12px;")
        footer_layout.addWidget(create_account)
        
        footer_layout.addStretch()
        
        # Realm Bridge logo
        rb_logo = QLabel()
        rb_logo_path = DICE_LINK_DIR / "static" / "Logos" / "RB_Logo_No_Background.png"
        if rb_logo_path.exists():
            rb_pixmap = QPixmap(str(rb_logo_path))
            rb_scaled = rb_pixmap.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation)
            rb_logo.setPixmap(rb_scaled)
        footer_layout.addWidget(rb_logo)
        
        layout.addLayout(footer_layout)
    
    def _on_connect(self):
        """Handle connect button click."""
        vtt_type = self.vtt_combo.currentText()
        vtt_address = self.address_input.text()
        username = self.username_input.text()
        
        # Emit signal with connection data
        self.connect_successful.emit(vtt_type, vtt_address, username)
        self.login_successful = True
        self.close()
    
    def exec(self) -> bool:
        """Show dialog and return True if login was successful."""
        self.show()
        return self.login_successful
