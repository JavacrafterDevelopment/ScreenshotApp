import sys
import os
import time
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFileDialog, QGridLayout)
from PyQt6.QtGui import QIcon

from qfluentwidgets import (FluentWindow, SubtitleLabel, LineEdit, PushButton, 
                            SpinBox, BodyLabel, Theme, setTheme, TitleLabel, 
                            CardWidget, PrimaryPushButton, ToolButton, InfoBar, InfoBarPosition)

import keyboard
import mss
from PIL import Image

class ScreenshotEngine(QThread):
    screenshot_taken = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.save_dir = ""
        self.prefix = "Screenshot"
        self.counter = 1
        
        self.is_running = False
        self.is_paused = False
        self.interval = 10  # seconds
        
        self.manual_requested = False
        
        self.sct = mss.mss()

    def run(self):
        self.is_running = True
        last_auto_time = time.time() - self.interval # Force immediate first shot

        while self.is_running:
            current_time = time.time()
            
            # Check manual trigger
            if self.manual_requested:
                self.take_screenshot(manual=True)
                self.manual_requested = False
                
            # Check auto trigger
            elif not self.is_paused and (current_time - last_auto_time) >= self.interval:
                self.take_screenshot(manual=False)
                last_auto_time = current_time
                
            time.sleep(0.1)

    def trigger_manual(self):
        if self.is_running:
            self.manual_requested = True
        else:
            # If auto isn't running, just take one now on the main thread or spin up logic
            self.take_screenshot(manual=True)

    def take_screenshot(self, manual=False):
        if not self.save_dir or not os.path.exists(self.save_dir):
            self.error_occurred.emit("Save directory does not exist.")
            return

        # Naming rule
        if manual:
            filename = f"{self.prefix}_- MANUAL - {self.counter}.png"
        else:
            filename = f"{self.prefix}_{self.counter}.png"
            
        filepath = os.path.join(self.save_dir, filename)
        
        try:
            # Capture all monitors
            monitor = self.sct.monitors[0]
            sct_img = self.sct.grab(monitor)
            
            # Save using PIL
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(filepath, "PNG")
            
            self.counter += 1
            self.screenshot_taken.emit(filename)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ScreenshotInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ScreenshotInterface")
        
        self.engine = ScreenshotEngine()
        self.engine.screenshot_taken.connect(self.on_screenshot_taken)
        self.engine.error_occurred.connect(self.on_error)
        self.engine.start() # Start the background thread
        self.engine.is_paused = True # Start paused

        self.hotkey_hook = None
        self.current_hotkey = "f9"

        self.setup_ui()
        self.register_hotkey(self.current_hotkey)

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.main_layout.setSpacing(24)

        # Title
        self.title_label = TitleLabel("Screenshot Configuration", self)
        self.main_layout.addWidget(self.title_label)

        # Top Section: Directory and Prefix
        self.top_card = CardWidget(self)
        self.top_layout = QGridLayout(self.top_card)
        
        self.dir_label = BodyLabel("Save Directory:", self)
        self.dir_input = LineEdit(self)
        self.dir_input.setText(os.path.abspath(os.path.expanduser("~\\Pictures")))
        self.engine.save_dir = self.dir_input.text()
        self.browse_btn = PushButton("Browse", self)
        self.browse_btn.clicked.connect(self.browse_dir)
        
        self.prefix_label = BodyLabel("Base File Name:", self)
        self.prefix_input = LineEdit(self)
        self.prefix_input.setText("Screenshot")
        self.prefix_input.textChanged.connect(self.update_prefix)

        self.top_layout.addWidget(self.dir_label, 0, 0)
        self.top_layout.addWidget(self.dir_input, 0, 1)
        self.top_layout.addWidget(self.browse_btn, 0, 2)
        
        self.top_layout.addWidget(self.prefix_label, 1, 0)
        self.top_layout.addWidget(self.prefix_input, 1, 1, 1, 2)
        
        self.main_layout.addWidget(self.top_card)

        # Bottom Section: Split
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setSpacing(24)

        # Left Side: Auto
        self.left_card = CardWidget(self)
        self.left_layout = QVBoxLayout(self.left_card)
        self.left_layout.setSpacing(16)
        
        self.auto_title = SubtitleLabel("Auto Screenshots", self)
        self.left_layout.addWidget(self.auto_title)
        
        self.interval_layout = QHBoxLayout()
        self.interval_label = BodyLabel("Interval (seconds):", self)
        self.interval_spin = SpinBox(self)
        self.interval_spin.setRange(1, 3600)
        self.interval_spin.setValue(10)
        self.interval_spin.valueChanged.connect(self.update_interval)
        self.interval_layout.addWidget(self.interval_label)
        self.interval_layout.addWidget(self.interval_spin)
        self.left_layout.addLayout(self.interval_layout)
        
        self.controls_layout = QHBoxLayout()
        self.start_btn = PrimaryPushButton("Start Auto", self)
        self.pause_btn = PushButton("Pause", self)
        self.stop_btn = PushButton("Stop/Reset", self)
        
        self.start_btn.clicked.connect(self.start_auto)
        self.pause_btn.clicked.connect(self.pause_auto)
        self.stop_btn.clicked.connect(self.stop_auto)
        
        self.controls_layout.addWidget(self.start_btn)
        self.controls_layout.addWidget(self.pause_btn)
        self.controls_layout.addWidget(self.stop_btn)
        self.left_layout.addLayout(self.controls_layout)
        
        self.bottom_layout.addWidget(self.left_card)

        # Right Side: Manual
        self.right_card = CardWidget(self)
        self.right_layout = QVBoxLayout(self.right_card)
        self.right_layout.setSpacing(16)
        
        self.manual_title = SubtitleLabel("Manual Screenshots", self)
        self.right_layout.addWidget(self.manual_title)
        
        self.hotkey_layout = QHBoxLayout()
        self.hotkey_label = BodyLabel("Global Hotkey:", self)
        self.hotkey_input = LineEdit(self)
        self.hotkey_input.setText(self.current_hotkey)
        self.hotkey_btn = PushButton("Set Key", self)
        self.hotkey_btn.clicked.connect(self.set_hotkey)
        
        self.hotkey_layout.addWidget(self.hotkey_label)
        self.hotkey_layout.addWidget(self.hotkey_input)
        self.hotkey_layout.addWidget(self.hotkey_btn)
        self.right_layout.addLayout(self.hotkey_layout)
        
        self.manual_btn = PushButton("Take Manual Screenshot Now", self)
        self.manual_btn.clicked.connect(self.engine.trigger_manual)
        self.right_layout.addWidget(self.manual_btn)
        
        self.status_label = BodyLabel("Status: Idle", self)
        self.right_layout.addWidget(self.status_label)
        
        self.bottom_layout.addWidget(self.right_card)

        self.main_layout.addLayout(self.bottom_layout)
        self.main_layout.addStretch(1)

    def browse_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.dir_input.text())
        if dir_path:
            self.dir_input.setText(dir_path)
            self.engine.save_dir = dir_path

    def update_prefix(self):
        self.engine.prefix = self.prefix_input.text()

    def update_interval(self):
        self.engine.interval = self.interval_spin.value()

    def start_auto(self):
        self.engine.is_paused = False
        self.status_label.setText("Status: Auto Running")
        InfoBar.success("Started", "Auto screenshots started.", duration=2000, parent=self)

    def pause_auto(self):
        self.engine.is_paused = True
        self.status_label.setText("Status: Auto Paused")
        InfoBar.warning("Paused", "Auto screenshots paused.", duration=2000, parent=self)

    def stop_auto(self):
        self.engine.is_paused = True
        self.engine.counter = 1
        self.status_label.setText("Status: Stopped (Counter Reset)")
        InfoBar.error("Stopped", "Auto screenshots stopped and counter reset.", duration=2000, parent=self)

    def set_hotkey(self):
        new_key = self.hotkey_input.text().strip().lower()
        if new_key:
            self.register_hotkey(new_key)
            
    def register_hotkey(self, key):
        try:
            if self.hotkey_hook:
                keyboard.remove_hotkey(self.hotkey_hook)
            self.hotkey_hook = keyboard.add_hotkey(key, self.engine.trigger_manual)
            self.current_hotkey = key
            self.hotkey_input.setText(key)
            InfoBar.success("Hotkey Set", f"Manual screenshot key set to '{key}'.", duration=2000, parent=self)
        except Exception as e:
            InfoBar.error("Hotkey Error", f"Failed to bind '{key}': {str(e)}", duration=3000, parent=self)

    @pyqtSlot(str)
    def on_screenshot_taken(self, filename):
        self.status_label.setText(f"Saved: {filename}")

    @pyqtSlot(str)
    def on_error(self, err):
        self.status_label.setText(f"Error: {err}")
        InfoBar.error("Screenshot Error", err, duration=3000, parent=self)

    def closeEvent(self, event):
        self.engine.is_running = False
        self.engine.wait()
        super().closeEvent(event)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screenshot App")
        self.resize(800, 600)
        
        # Add the main interface
        self.screenshot_interface = ScreenshotInterface(self)
        # We must add it to the window
        # The first argument is the widget, second is an icon (can be None or standard), third is the text
        self.addSubInterface(self.screenshot_interface, QIcon(), "Screenshots")

if __name__ == '__main__':
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # Auto detect dark/light theme
    setTheme(Theme.AUTO)
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())
