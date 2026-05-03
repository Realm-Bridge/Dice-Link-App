"""
Realm Bridge / Dice Link - Startup Dialog Module
Initial login and VTT selection dialog shown on application startup.
Uses HTML/CSS rendered via QWebEngineView for consistent styling with main window.
Uses identical architecture to main.py - DraggableWebEngineView as the window itself.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QIcon
from pathlib import Path

from vtt_web import DraggableWebEngineView
from window_controller import WindowController
from debug import log_startup_dialog

# Resolve the directory of this file
DICE_LINK_DIR = Path(__file__).resolve().parent


class StartupWindowController(WindowController):
    """
    Extends WindowController with login functionality for the startup dialog.
    Inherits: minimize(), close(), startDrag(), doDrag() from WindowController.
    Adds: login() for form submission.
    Re-declares inherited methods with @pyqtSlot for JavaScript access.
    """

    # Signal emitted when user successfully logs in
    login_successful = pyqtSignal(str, str, str)  # vtt_type, vtt_address, username

    @pyqtSlot()
    def minimize(self):
        """Minimize the window."""
        log_startup_dialog("minimize() called from JavaScript")
        super().minimize()

    @pyqtSlot()
    def close(self):
        """Close the window."""
        log_startup_dialog("close() called from JavaScript")
        super().close()

    @pyqtSlot(int, int)
    def startDrag(self, pos_x: int, pos_y: int):
        """Start dragging the window."""
        log_startup_dialog(f"startDrag({pos_x}, {pos_y}) called from JavaScript")
        super().startDrag(pos_x, pos_y)

    @pyqtSlot(int, int)
    def doDrag(self, pos_x: int, pos_y: int):
        """Continue dragging the window."""
        log_startup_dialog(f"doDrag({pos_x}, {pos_y}) called from JavaScript")
        super().doDrag(pos_x, pos_y)

    @pyqtSlot(str, str, str, str)
    def login(self, vtt_type: str, vtt_address: str, username: str, password: str):
        """
        Called by JavaScript when user clicks Connect button.
        Opens main DLA window and closes startup dialog.
        """
        log_startup_dialog("login() called, opening main window")
        self.login_successful.emit(vtt_type, vtt_address, username)


class StartupDialog(DraggableWebEngineView):
    """
    Initial login dialog shown on application startup.
    Uses HTML/CSS rendered via QWebEngineView for consistent styling.
    Uses identical architecture to main DLA window - DraggableWebEngineView as the window itself.
    """

    # Signal emitted when user successfully connects
    connect_successful = pyqtSignal(str, str, str)  # vtt_type, vtt_address, username

    def __init__(self, server_port: int = 8765):
        super().__init__()
        log_startup_dialog("StartupDialog.__init__ started")

        self.server_port = server_port

        # Ensure page is initialized (same as main.py line 157)
        self.setPage(self.page())
        log_startup_dialog("Page initialized")

        # Enable transparent background for rounded corners (same as main.py line 160)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Set up window controller for frameless window control (same as main.py lines 162-163)
        # Uses StartupWindowController which extends WindowController with login()
        self.window_controller = StartupWindowController(self, self)
        log_startup_dialog("WindowController created")

        # Connect login signal to our connect_successful signal
        self.window_controller.login_successful.connect(self._on_login_successful)

        # Set window properties (same as main.py lines 165-166)
        self.setWindowTitle("Dice Link Login")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # Set window icon (same as main.py lines 168-170)
        logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background_small.ico"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        # Set up web channel for JavaScript-to-Python communication (same as main.py lines 172-174)
        self.channel = QWebChannel()
        self.channel.registerObject("pyqtBridge", self.window_controller)
        self.page().setWebChannel(self.channel)
        log_startup_dialog("WebChannel set up with pyqtBridge")

        # Connect loadFinished to inject qwebchannel.js (same pattern as VTTWebView)
        self.page().loadFinished.connect(self.on_page_loaded)

        # Set designed dimensions — zoom and aspect ratio are derived from these
        self._designed_width = 550
        self._designed_height = 650
        self.setMinimumSize(300, 354)  # maintains 550:650 ratio at minimum width

        # Open at designed size if it fits the screen; otherwise scale to 30% of screen width
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        if screen_rect.width() >= 550 and screen_rect.height() >= 650:
            self.resize(550, 650)
        else:
            initial_width = int(screen_rect.width() * 0.3)
            initial_height = int(initial_width * 650 / 550)
            self.resize(initial_width, initial_height)

        # Load the startup HTML page from the server (same as main.py line 194)
        self.load(QUrl(f"http://localhost:{self.server_port}/startup"))
        log_startup_dialog("StartupDialog.__init__ complete, URL loading")

    def on_page_loaded(self, ok):
        """Called when page finishes loading - inject qwebchannel.js"""
        if not ok:
            log_startup_dialog("Page load failed")
            return

        log_startup_dialog("Page loaded, injecting QWebChannel.js...")

        # Inject the qwebchannel.js library dynamically
        load_qwebchannel_js = """
        (function() {
            return new Promise(function(resolve, reject) {
                var script = document.createElement('script');
                script.src = 'qrc:///qtwebchannel/qwebchannel.js';
                script.onload = function() {
                    resolve('QWebChannel.js loaded');
                };
                script.onerror = function() {
                    reject('Failed to load qwebchannel.js');
                };
                document.head.appendChild(script);
            });
        })();
        """

        def on_qwebchannel_loaded(result):
            log_startup_dialog(f"QWebChannel.js load result: {result}")
            self.attempt_initialize_webchannel(attempt=1, max_attempts=10)

        self.page().runJavaScript(load_qwebchannel_js, on_qwebchannel_loaded)

    def attempt_initialize_webchannel(self, attempt=1, max_attempts=10):
        """Try to initialize QWebChannel. Retry with backoff if not ready."""
        check_script = "typeof QWebChannel !== 'undefined'"

        def on_check_result(is_available):
            if is_available:
                log_startup_dialog(f"QWebChannel detected (attempt {attempt}), initializing...")
                self.initialize_webchannel()
            elif attempt < max_attempts:
                wait_ms = min(50 * attempt, 500)
                log_startup_dialog(f"QWebChannel not ready (attempt {attempt}/{max_attempts}), retrying in {wait_ms}ms...")

                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self.attempt_initialize_webchannel(attempt + 1, max_attempts))
                timer.start(wait_ms)

                if not hasattr(self, '_init_timers'):
                    self._init_timers = []
                self._init_timers.append(timer)
            else:
                log_startup_dialog(f"ERROR: QWebChannel still not available after {max_attempts} attempts")

        self.page().runJavaScript(check_script, on_check_result)

    def initialize_webchannel(self):
        """Initialize the QWebChannel connection from JavaScript side"""
        init_script = """
        (function() {
            if (typeof QWebChannel === 'undefined') {
                return 'QWebChannel not defined';
            }
            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.pyqtBridge = channel.objects.pyqtBridge;
                console.log('[StartupDialog] pyqtBridge connected:', window.pyqtBridge);

                // Trigger any pending initialization
                if (typeof initWindowControls === 'function') {
                    initWindowControls();
                }
            });
            return 'QWebChannel initialization started';
        })();
        """

        def on_init_result(result):
            log_startup_dialog(f"WebChannel init result: {result}")

        self.page().runJavaScript(init_script, on_init_result)

    def _on_login_successful(self, vtt_type: str, vtt_address: str, username: str):
        """
        Called when user logs in successfully.
        Emits connect_successful signal for main.py to handle, then closes this dialog.
        """
        log_startup_dialog("Login successful, emitting connect_successful signal")
        self.connect_successful.emit(vtt_type, vtt_address, username)
