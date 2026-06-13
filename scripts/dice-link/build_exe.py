"""
PyInstaller Build Script for Dice Link App

Run from the dice-link/ directory:
    python build_exe.py

Output: dist/DiceLink/ (directory bundle — see NOTE 1 below)

=============================================================================
BEFORE YOU RUN THIS
=============================================================================

Install PyInstaller if not already installed:
    pip install pyinstaller

Then do a test build and verify the .exe launches correctly before distributing.

=============================================================================
KNOWN PACKAGING CHALLENGES — READ BEFORE TOUCHING
=============================================================================

NOTE 1 — Use --onedir, NOT --onefile
    QWebEngineProcess.exe (a required Qt subprocess) must sit next to the main
    .exe at runtime. PyInstaller's --onefile mode extracts to a temp dir on
    each launch, which breaks Qt's process discovery. Use --onedir instead.
    The output will be a folder (dist/DiceLink/), not a single file. Zip it
    for distribution.

NOTE 2 — Qt WebEngine binaries
    PyInstaller does not auto-collect all Qt WebEngine assets. You will likely
    need one or more of these flags:
        --collect-all PyQt6
    or manually add --add-binary entries for:
        QtWebEngineCore, QtWebEngineWidgets, QtWebEngineProcess.exe,
        Qt6Core.dll, Qt6Gui.dll, Qt6Widgets.dll, Qt6Network.dll,
        Qt6WebChannel.dll, Qt6Positioning.dll
    The exact set depends on the PyQt6 version. Run the built .exe and check
    what DLLs it complains about missing.

NOTE 3 — Qt plugins
    Qt needs its plugins folder (platforms/, imageformats/, etc.) alongside
    the .exe. PyInstaller usually collects these automatically when using
    --collect-all PyQt6, but verify in the output dist/DiceLink/ folder.

NOTE 4 — aiortc / aioice
    aiortc has native dependencies (libvpx, libopus via av/PyAV). These need
    to be bundled. Try:
        --collect-all aiortc
        --collect-all av
    If av is not installed (phone camera WebRTC not in use), aiortc may not
    be needed at all — check imports in server.py first.

NOTE 5 — Hidden imports
    FastAPI and uvicorn use dynamic imports for their ASGI drivers. Add:
        --hidden-import uvicorn.lifespan.on
        --hidden-import uvicorn.logging
        --hidden-import uvicorn.protocols.http.auto
        --hidden-import uvicorn.protocols.websockets.auto
        --hidden-import uvicorn.loops.auto

NOTE 6 — QWebChannel transport
    The qwebchannel.js file served via qrc:///qtwebchannel/qwebchannel.js
    is embedded in the Qt DLLs, not in our source tree. It should be
    available automatically as long as the Qt DLLs are bundled correctly.

NOTE 7 — Console window
    --windowed hides the console. During testing, remove this flag so you can
    see Python tracebacks if the app crashes on startup.

=============================================================================
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "DiceLink"
MAIN_SCRIPT = "main.py"


def clean_build_dirs():
    for dir_name in ['build', 'dist', '__pycache__']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned: {dir_name}/")


def build_exe():
    cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--onedir',       # Do NOT change to --onefile — see NOTE 1 above
        '--windowed',     # Remove this flag while debugging startup crashes
        '--clean',

        # Source data
        '--add-data', 'templates;templates',
        '--add-data', 'static;static',

        # Qt WebEngine — expand this if the .exe fails to start (see NOTE 2)
        '--collect-all', 'PyQt6',

        # FastAPI / uvicorn async drivers (see NOTE 5)
        '--hidden-import', 'uvicorn.lifespan.on',
        '--hidden-import', 'uvicorn.logging',
        '--hidden-import', 'uvicorn.protocols.http.auto',
        '--hidden-import', 'uvicorn.protocols.websockets.auto',
        '--hidden-import', 'uvicorn.loops.auto',

        # TODO: add --collect-all aiortc and --collect-all av if phone camera
        # WebRTC is being bundled (see NOTE 4)

        # TODO: set icon once one exists
        # '--icon', 'static/icon.ico',

        MAIN_SCRIPT
    ]

    print("Building executable...")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        subprocess.run(cmd, check=True)
        dist_path = Path(f'dist/{APP_NAME}')
        print(f"\nBuild successful — output: {dist_path.resolve()}")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)


def main():
    print("=" * 60)
    print(f"Building {APP_NAME} with PyInstaller")
    print("=" * 60)

    print("\n[1/2] Cleaning build directories...")
    clean_build_dirs()

    print("\n[2/2] Building executable...")
    build_exe()

    print("\n" + "=" * 60)
    print("Build complete. Test the .exe before distributing.")
    print("=" * 60)


if __name__ == '__main__':
    main()
