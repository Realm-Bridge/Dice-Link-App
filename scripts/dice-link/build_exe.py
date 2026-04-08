"""
PyInstaller Build Script

Creates a standalone Windows .exe for Dice Link App.
Run: python build_exe.py

Output: dist/DiceLink.exe (~100-150MB)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# PyInstaller configuration
APP_NAME = "DiceLink"
MAIN_SCRIPT = "main.py"
ICON_PATH = "static/icon.ico"  # TODO: Create app icon


def clean_build_dirs():
    """Remove old build artifacts."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned: {dir_name}/")


def build_exe():
    """Run PyInstaller to create .exe."""
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--onefile',  # Single .exe file
        '--windowed',  # No console window
        '--clean',
        
        # Include data files
        '--add-data', 'templates;templates',
        '--add-data', 'static;static',
        
        # Include models directory (with bundled v1.0.0 model)
        # '--add-data', 'models;models',
        
        # Hidden imports (if needed for ONNX/Flask)
        '--hidden-import', 'engineio.async_drivers.threading',
        '--hidden-import', 'flask',
        '--hidden-import', 'webview',
        
        # Icon (when available)
        # '--icon', ICON_PATH,
        
        # Main entry point
        MAIN_SCRIPT
    ]
    
    print("Building executable...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n✓ Build successful!")
        print(f"Executable: dist/{APP_NAME}.exe")
        print(f"Size: {get_file_size(f'dist/{APP_NAME}.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        sys.exit(1)


def get_file_size(file_path):
    """Get human-readable file size."""
    size_bytes = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def main():
    """Main build process."""
    print("=" * 60)
    print(f"Building {APP_NAME} with PyInstaller")
    print("=" * 60)
    
    # Step 1: Clean old builds
    print("\n[1/2] Cleaning build directories...")
    clean_build_dirs()
    
    # Step 2: Build .exe
    print("\n[2/2] Building executable...")
    build_exe()
    
    print("\n" + "=" * 60)
    print("Build complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
