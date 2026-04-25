"""
Realm Bridge / Dice Link - Custom Window Module
Provides reusable custom title bar, buttons, resize grip, and base window class
for all frameless windows in the application.
"""

from pathlib import Path
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QPixmap, QFont, QIcon
from PyQt6.QtCore import Qt

# Resolve the directory of this file so logo paths work regardless of cwd
DICE_LINK_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Shared color constants matching the DLA main window
# ---------------------------------------------------------------------------
COLOR_BG         = "#0f1419"
COLOR_PURPLE     = "#6f2e9a"
COLOR_TEXT       = "#f0f2f5"
COLOR_BTN_HOVER  = "rgba(139, 92, 246, 0.1)"
COLOR_CLOSE_HOVER_BG   = "rgba(239, 68, 68, 0.2)"
COLOR_CLOSE_HOVER_TEXT = "#ef4444"

# ---------------------------------------------------------------------------
# Individual button classes - each carries its own correct styling
# ---------------------------------------------------------------------------

class MinimizeButton(QPushButton):
    """Window minimize button styled to match DLA theme"""

    def __init__(self, parent=None):
        super().__init__("−", parent)
        self.setFixedSize(36, 36)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLOR_PURPLE};
                font-size: 28px;
                font-weight: normal;
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BTN_HOVER};
            }}
        """)


class MaximizeButton(QPushButton):
    """Window maximize/restore button styled to match DLA theme.
    Uses □ square character (24px) for maximize and ❐ (18px) for restore.
    """

    def __init__(self, parent=None):
        super().__init__("□", parent)
        self.setFixedSize(36, 36)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLOR_PURPLE};
                font-size: 24px;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BTN_HOVER};
            }}
        """)

    def set_maximized(self, is_maximized: bool):
        """Switch the button character between maximize and restore states.
        Restore character is smaller (18px) to fit in the button.
        """
        if is_maximized:
            self.setText("❐")
            # Temporarily reduce font size for the wider restore character
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {COLOR_PURPLE};
                    font-size: 18px;
                    font-weight: bold;
                    padding: 8px 12px;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BTN_HOVER};
                }}
            """)
        else:
            self.setText("□")
            # Restore normal font size for maximize character
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {COLOR_PURPLE};
                    font-size: 24px;
                    font-weight: bold;
                    padding: 8px 12px;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BTN_HOVER};
                }}
            """)


class CloseButton(QPushButton):
    """Window close button styled to match DLA theme"""

    def __init__(self, parent=None):
        super().__init__("×", parent)
        self.setObjectName("closeBtn")
        self.setFixedSize(36, 36)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLOR_PURPLE};
                font-size: 28px;
                font-weight: normal;
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_CLOSE_HOVER_BG};
                color: {COLOR_CLOSE_HOVER_TEXT};
            }}
        """)


class SettingsButton(QPushButton):
    """Settings/gear button styled to match DLA theme"""

    def __init__(self, parent=None):
        super().__init__("⚙", parent)
        self.setFixedSize(36, 36)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLOR_PURPLE};
                font-size: 20px;
                font-weight: normal;
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BTN_HOVER};
            }}
        """)


# ---------------------------------------------------------------------------
# Reusable custom title bar
# ---------------------------------------------------------------------------

class CustomTitleBar(QWidget):
    """Custom title bar for all Realm Bridge / Dice Link windows.

    Parameters
    ----------
    parent_window : QMainWindow
        The window this title bar belongs to and controls.
    show_maximize : bool
        Whether to include the maximize/restore button (default True).
    show_settings : bool
        Whether to include the settings button (default False).
    title : str
        Title text to display (empty string hides the title).
    settings_callback : callable
        Function to call when settings button is clicked.
    """

    def __init__(self, parent_window, show_maximize: bool = True, show_settings: bool = False, title: str = "", settings_callback=None):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.show_maximize = show_maximize
        self.show_settings = show_settings
        self.settings_callback = settings_callback
        self.drag_position = None

        self.setFixedHeight(40)
        self.setStyleSheet(f"QWidget {{ background-color: {COLOR_BG}; }}")
        # Lock the cursor to arrow on the title bar so resize cursors never bleed in
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setMouseTracking(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        # Dice Link logo (left side)
        self.dice_link_logo = QLabel()
        logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            scaled = pixmap.scaledToHeight(44, Qt.TransformationMode.SmoothTransformation)
            self.dice_link_logo.setPixmap(scaled)
        layout.addWidget(self.dice_link_logo)

        # Title label (center) - only if title is provided
        if title:
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLOR_PURPLE};
                    font-size: 14px;
                    font-weight: normal;
                }}
            """)
            self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.title_label, 1)  # Give it stretch factor
        else:
            self.title_label = None
            layout.addStretch(1)  # Add stretch if no title

        # Settings button (optional)
        if self.show_settings:
            self.settings_btn = SettingsButton()
            if self.settings_callback:
                self.settings_btn.clicked.connect(self.settings_callback)
            layout.addWidget(self.settings_btn)
        else:
            self.settings_btn = None

        # Minimize button
        self.minimize_btn = MinimizeButton()
        self.minimize_btn.clicked.connect(self._minimize)
        layout.addWidget(self.minimize_btn)

        # Maximize button (optional)
        if self.show_maximize:
            self.maximize_btn = MaximizeButton()
            self.maximize_btn.clicked.connect(self._toggle_maximize)
            layout.addWidget(self.maximize_btn)
        else:
            self.maximize_btn = None

        # Close button
        self.close_btn = CloseButton()
        self.close_btn.clicked.connect(self._close)
        layout.addWidget(self.close_btn)

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def _minimize(self):
        self.parent_window.showMinimized()

    def _toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()
        if self.maximize_btn:
            self.maximize_btn.set_maximized(self.parent_window.isMaximized())

    def _close(self):
        self.parent_window.close()

    def set_title(self, title: str):
        """Update the title displayed in the title bar."""
        if self.title_label:
            self.title_label.setText(title)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint()
                - self.parent_window.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.parent_window.move(
                event.globalPosition().toPoint() - self.drag_position
            )
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None


# ---------------------------------------------------------------------------
# Invisible resize grip (bottom-right corner)
# ---------------------------------------------------------------------------

class ResizeGrip(QWidget):
    """Small invisible widget placed at the bottom-right corner of a frameless
    window to allow the user to resize it by dragging."""

    def __init__(self, parent_window, grip_size: int = 16):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.resize_start_pos = None
        self.resize_start_geometry = None

        self.setFixedSize(grip_size, grip_size)
        self.setStyleSheet("background-color: transparent;")
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resize_start_pos = event.globalPosition().toPoint()
            self.resize_start_geometry = self.parent_window.geometry()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.resize_start_pos:
            diff = event.globalPosition().toPoint() - self.resize_start_pos
            geo = self.resize_start_geometry
            new_geo = self.parent_window.geometry()
            new_geo.setRight(geo.right() + diff.x())
            new_geo.setBottom(geo.bottom() + diff.y())
            if (new_geo.width() >= self.parent_window.minimumWidth()
                    and new_geo.height() >= self.parent_window.minimumHeight()):
                self.parent_window.setGeometry(new_geo)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.resize_start_pos = None
        self.resize_start_geometry = None


# ---------------------------------------------------------------------------
# Base custom window class
# ---------------------------------------------------------------------------

class CustomWindow(QMainWindow):
    """Base class for all Realm Bridge / Dice Link frameless windows.

    Subclasses should:
    - Call super().__init__(show_maximize=..., resizable=...)
    - Use self.content_layout (QVBoxLayout) to add their content widgets
    - Override closeEvent() as needed, calling super().closeEvent(event) last

    Parameters
    ----------
    show_maximize : bool
        Whether to show the maximize button in the title bar (default True).
    resizable : bool
        Whether to add a bottom-right resize grip (default True).
    """

    def __init__(self, show_maximize: bool = True, resizable: bool = True, title: str = "", show_settings: bool = False, settings_callback=None):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(400, 300)
        self.setWindowTitle(title)
        
        # Set window icon for taskbar branding
        logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background_small.ico"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        # Central widget
        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {COLOR_BG};")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        self.title_bar = CustomTitleBar(self, show_maximize=show_maximize, show_settings=show_settings, title=title, settings_callback=settings_callback)
        main_layout.addWidget(self.title_bar)

        # Content area - subclasses add their widgets here
        self.content_layout = main_layout

        # Resize grip
        self.resize_grip = None
        if resizable:
            self.resize_grip = ResizeGrip(self)
            self.resize_grip.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.resize_grip:
            grip_size = self.resize_grip.width()
            self.resize_grip.move(
                self.width() - grip_size,
                self.height() - grip_size
            )
