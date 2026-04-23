import os
import subprocess
import sys

def build():
    print("Starting build process...")
    # Use PyInstaller to build a portable directory (onedir mode is default when -F is not specified, but we'll use -D explicitly)
    # We use -w to disable the console window so only the GUI shows.
    # We name the executable "ScreenshotApp"
    
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "ScreenshotApp",
        "main.py"
    ]
    
    subprocess.run(command, check=True)
    print("Build finished! The portable folder is located in the 'dist' directory.")

if __name__ == "__main__":
    build()
