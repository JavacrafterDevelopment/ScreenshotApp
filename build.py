import os
import shutil
import subprocess
import sys

def build():
    print("Starting build process...")
    
    # Use PyInstaller to build a portable directory (onedir mode)
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
    
    # Copy the built output to the SCREENSHOTAPP_PORTABLE folder
    dist_dir = os.path.join(os.path.dirname(__file__), "dist", "ScreenshotApp")
    portable_dir = os.path.join(os.path.dirname(__file__), "SCREENSHOTAPP_PORTABLE")
    
    if os.path.exists(dist_dir):
        print(f"Copying build output to {portable_dir}...")
        
        # Remove old portable folder contents (keep the folder itself for git)
        if os.path.exists(portable_dir):
            shutil.rmtree(portable_dir)
        
        # Copy the new build
        shutil.copytree(dist_dir, portable_dir)
        print(f"Portable app updated at: {portable_dir}")
    else:
        print(f"WARNING: Expected build output at {dist_dir} not found!")
    
    print("Build finished!")

if __name__ == "__main__":
    build()
