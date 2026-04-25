"""
Realm Bridge / Dice Link - Startup Dialog Module
Initial login and VTT selection dialog shown on application startup
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QComboBox, QPasswordEdit
)
from PyQt6.QtGui import QPixmap, QFont, QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from custom_window import CustomWindow

# Resolve the directory of this file so logo paths work
DICE_LINK_DIR = Path(__file__).resolve().parent


class StartupDialog(CustomWindow):
    """
    Initial login dialog shown on application startup.
    Allows user to select VTT, enter connection details, and credentials.
    """
    
    # Signal emitted when user successfully connects
    connect_successful = pyqtSignal(str, str, str)  # vtt_type, vtt_address, username
    
    def __init__(self, parent=None):
        super().__init__(show_maximize=False, resizable=False, title="Dice Link Login", parent=parent)
        
        # Set window size
        self.setFixedSize(550, 600)
        
        # Create main content widget
        content_widget = QWidget()
        self.content_layout.addWidget(content_widget)
        
        # Create main layout for content
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # ===== FORM SECTION =====
        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)
        
        # --- VTT Selection Row ---
        vtt_row = QHBoxLayout()
        vtt_label = QLabel("Connect me to:")
        vtt_label.setFixedWidth(120)
        vtt_label.setFont(QFont("Arial", 11))
        self.vtt_dropdown = QComboBox()
        self.vtt_dropdown.setMinimumHeight(32)
        self.vtt_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #1a1f2e;
                color: #f0f2f5;
                border: 1px solid #6f2e9a;
                border-radius: 4px;
                padding: 5px;
                font-size: 10px;
            }
            QComboBox:hover {
                border: 1px solid #8b5cf6;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1f2e;
                color: #f0f2f5;
                selection-background-color: #6f2e9a;
            }
        """)
        
        # Populate VTT dropdown - Active first, then greyed out
        self._populate_vtt_dropdown()
        
        vtt_row.addWidget(vtt_label)
        vtt_row.addWidget(self.vtt_dropdown)
        form_layout.addLayout(vtt_row)
        
        # --- VTT Address Row ---
        address_row = QHBoxLayout()
        address_label = QLabel("VTT Address:")
        address_label.setFixedWidth(120)
        address_label.setFont(QFont("Arial", 11))
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("http://localhost:30000 or https://example.com")
        self.address_input.setMinimumHeight(32)
        self.address_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1f2e;
                color: #f0f2f5;
                border: 1px solid #6f2e9a;
                border-radius: 4px;
                padding: 5px;
                font-size: 10px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        address_row.addWidget(address_label)
        address_row.addWidget(self.address_input)
        form_layout.addLayout(address_row)
        
        # --- Username Row ---
        username_row = QHBoxLayout()
        username_label = QLabel("User Name:")
        username_label.setFixedWidth(120)
        username_label.setFont(QFont("Arial", 11))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Usually Email")
        self.username_input.setMinimumHeight(32)
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1f2e;
                color: #f0f2f5;
                border: 1px solid #6f2e9a;
                border-radius: 4px;
                padding: 5px;
                font-size: 10px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        username_row.addWidget(username_label)
        username_row.addWidget(self.username_input)
        form_layout.addLayout(username_row)
        
        # --- Password Row ---
        password_row = QHBoxLayout()
        password_label = QLabel("Password:")
        password_label.setFixedWidth(120)
        password_label.setFont(QFont("Arial", 11))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(32)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1f2e;
                color: #f0f2f5;
                border: 1px solid #6f2e9a;
                border-radius: 4px;
                padding: 5px;
                font-size: 10px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        password_row.addWidget(password_label)
        password_row.addWidget(self.password_input)
        form_layout.addLayout(password_row)
        
        main_layout.addLayout(form_layout)
        
        # ===== ERROR MESSAGE LABEL =====
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #ff6b6b; font-size: 10px;")
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        main_layout.addWidget(self.error_label)
        
        # ===== SPACER =====
        main_layout.addStretch()
        
        # ===== CONNECT BUTTON =====
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f2e9a;
                color: #f0f2f5;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8b5cf6;
            }
            QPushButton:pressed {
                background-color: #5a1f7c;
            }
        """)
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        main_layout.addWidget(self.connect_btn)
        
        # ===== FOOTER SECTION =====
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)
        
        # Create free account link
        self.create_account_link = QPushButton("Create Free Account")
        self.create_account_link.setFlat(True)
        self.create_account_link.setStyleSheet("""
            QPushButton {
                color: #8b5cf6;
                background: transparent;
                border: none;
                text-decoration: underline;
                font-size: 10px;
            }
            QPushButton:hover {
                color: #a78bfa;
            }
        """)
        self.create_account_link.clicked.connect(self.on_create_account_clicked)
        footer_layout.addWidget(self.create_account_link)
        
        # Realm Bridge logo
        footer_layout.addStretch()
        
        realm_logo_label = QLabel()
        realm_logo_path = DICE_LINK_DIR / "static" / "Logos" / "rb_logo.png"
        if realm_logo_path.exists():
            logo_pixmap = QPixmap(str(realm_logo_path))
            scaled_logo = logo_pixmap.scaledToHeight(24, Qt.TransformationMode.SmoothTransformation)
            realm_logo_label.setPixmap(scaled_logo)
        else:
            # Placeholder text if logo doesn't exist
            realm_logo_label.setText("Realm Bridge")
            realm_logo_label.setStyleSheet("color: #8b5cf6; font-size: 9px;")
        
        footer_layout.addWidget(realm_logo_label)
        
        main_layout.addLayout(footer_layout)
        
        # Store form data for later access
        self.form_data = {}
    
    def _populate_vtt_dropdown(self):
        """Populate VTT dropdown with active and disabled options in alphabetical order"""
        
        # Active VTTs (selectable)
        active_vtt = ["Foundry VTT"]
        
        # Greyed out / Road mapped VTTs (alphabetical)
        roadmap_vtt = [
            "Beyond Tabletop",
            "Discord",
            "DnD Beyond Maps",
            "Fantasy Grounds",
            "Game Master Engine",
            "Owlbear Rodeo",
            "Roll20",
            "Tabletop Simulator",
            "Tale Spire"
        ]
        
        # Add active VTTs
        for vtt in active_vtt:
            self.vtt_dropdown.addItem(vtt)
        
        # Add separator and roadmap VTTs
        self.vtt_dropdown.insertSeparator(len(active_vtt))
        for vtt in roadmap_vtt:
            self.vtt_dropdown.addItem(vtt)
            # Get index and disable it
            index = self.vtt_dropdown.count() - 1
            self.vtt_dropdown.model().item(index).setEnabled(False)
    
    def on_connect_clicked(self):
        """Handle Connect button click"""
        # For now, just collect the form data and show placeholder message
        vtt_type = self.vtt_dropdown.currentText()
        vtt_address = self.address_input.text().strip()
        username = self.username_input.text().strip()
        
        # Store form data
        self.form_data = {
            'vtt_type': vtt_type,
            'vtt_address': vtt_address,
            'username': username
        }
        
        # Emit signal with form data
        self.connect_successful.emit(vtt_type, vtt_address, username)
    
    def on_create_account_clicked(self):
        """Handle Create Free Account link click"""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        
        QDesktopServices.openUrl(QUrl("https://realmbridge.co.uk/"))
    
    def show_error(self, message):
        """Display error message to user"""
        self.error_label.setText(f"Error: {message}")
        self.error_label.setVisible(True)
    
    def clear_error(self):
        """Clear error message"""
        self.error_label.setVisible(False)
        self.error_label.setText("")
