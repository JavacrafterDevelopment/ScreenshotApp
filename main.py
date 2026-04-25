import sys
import os
import time
import subprocess
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFileDialog, QGridLayout, QListWidgetItem, QSystemTrayIcon)
from PyQt6.QtGui import QIcon

from qfluentwidgets import (FluentWindow, SubtitleLabel, LineEdit, PushButton, 
                            SpinBox, BodyLabel, Theme, setTheme, TitleLabel, 
                            CardWidget, PrimaryPushButton, ToolButton, InfoBar, 
                            ListWidget, ToggleButton, FluentIcon, ComboBox, SettingCardGroup,
                            OptionsSettingCard, ExpandLayout)

import keyboard
import mss
from PIL import Image

class HotkeyRecorder(QThread):
    hotkey_recorded = pyqtSignal(str)

    def run(self):
        # Blocks until a key combination is pressed
        hk = keyboard.read_hotkey(suppress=False)
        self.hotkey_recorded.emit(hk)

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
        self.format = "PNG"
        self.resolution_override = "Current Resolution"
        self.resolution = self.get_resolution()

    def get_resolution(self):
        monitor = self.sct.monitors[0]
        return f"{monitor['width']}x{monitor['height']}"

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
            self.take_screenshot(manual=True)

    def take_screenshot(self, manual=False):
        if not self.save_dir or not os.path.exists(self.save_dir):
            self.error_occurred.emit("Save directory does not exist.")
            return

        # Naming rule
        if manual:
            base_filename = f"{self.prefix}_- MANUAL - {self.counter}"
        else:
            base_filename = f"{self.prefix}_{self.counter}"
            
        ext = self.format.lower()
        filename = f"{base_filename}.{ext}"
        filepath = os.path.join(self.save_dir, filename)
        
        # Prevent overwrite by appending SET X
        set_num = 2
        while os.path.exists(filepath):
            filename = f"{base_filename} SET {set_num}.{ext}"
            filepath = os.path.join(self.save_dir, filename)
            set_num += 1
        
        try:
            # Capture all monitors
            monitor = self.sct.monitors[0]
            sct_img = self.sct.grab(monitor)
            
            # Save using PIL
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            # Apply resolution override if needed
            res_map = {
                "1080p": (1920, 1080),
                "1440p": (2560, 1440),
                "4k": (3840, 2160),
                "5k": (5120, 2880)
            }
            if self.resolution_override in res_map:
                target_size = res_map[self.resolution_override]
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            img.save(filepath, self.format)
            
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
        self.recorder = None

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(FluentIcon.CAMERA.icon())
        self.tray.show()

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
        self.hotkey_label = BodyLabel("Global Hotkey: " + self.current_hotkey, self)
        self.hotkey_btn = ToggleButton("Record New Key", self)
        self.hotkey_btn.clicked.connect(self.toggle_record_hotkey)
        
        self.hotkey_layout.addWidget(self.hotkey_label)
        self.hotkey_layout.addWidget(self.hotkey_btn)
        self.right_layout.addLayout(self.hotkey_layout)
        
        self.manual_btn = PushButton("Take Manual Screenshot Now", self)
        self.manual_btn.clicked.connect(self.engine.trigger_manual)
        self.right_layout.addWidget(self.manual_btn)
        
        self.status_label = BodyLabel("Status: Idle", self)
        self.right_layout.addWidget(self.status_label)
        
        self.bottom_layout.addWidget(self.right_card)

        self.main_layout.addLayout(self.bottom_layout)
        
        # Console Section
        self.console_card = CardWidget(self)
        self.console_layout = QVBoxLayout(self.console_card)
        self.console_layout.setSpacing(16)
        
        self.console_title = SubtitleLabel("Output Console (Double-click to view in explorer)", self)
        self.console_list = ListWidget(self)
        self.console_list.itemDoubleClicked.connect(self.open_in_explorer)
        
        self.console_layout.addWidget(self.console_title)
        self.console_layout.addWidget(self.console_list)
        
        self.main_layout.addWidget(self.console_card)

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

    def toggle_record_hotkey(self):
        if self.hotkey_btn.isChecked():
            self.hotkey_btn.setText("Listening...")
            self.recorder = HotkeyRecorder()
            self.recorder.hotkey_recorded.connect(self.on_hotkey_recorded)
            self.recorder.start()
        else:
            self.hotkey_btn.setText("Record New Key")

    @pyqtSlot(str)
    def on_hotkey_recorded(self, key):
        self.hotkey_btn.setChecked(False)
        self.hotkey_btn.setText("Record New Key")
        self.register_hotkey(key)

    def register_hotkey(self, key):
        try:
            if self.hotkey_hook:
                keyboard.remove_hotkey(self.hotkey_hook)
            self.hotkey_hook = keyboard.add_hotkey(key, self.engine.trigger_manual)
            self.current_hotkey = key
            self.hotkey_label.setText("Global Hotkey: " + key)
            InfoBar.success("Hotkey Set", f"Manual screenshot key set to '{key}'.", duration=2000, parent=self)
        except Exception as e:
            InfoBar.error("Hotkey Error", f"Failed to bind '{key}': {str(e)}", duration=3000, parent=self)

    @pyqtSlot(str)
    def on_screenshot_taken(self, filename):
        self.status_label.setText(f"Saved: {filename}")
        
        filepath = os.path.join(self.engine.save_dir, filename)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        item = QListWidgetItem(f"[{timestamp}] {filename}")
        item.setData(Qt.ItemDataRole.UserRole, filepath)
        self.console_list.insertItem(0, item)
        
        # Show Windows notification only for manual screenshots
        if "- MANUAL -" in filename:
            self.tray.showMessage("Screenshot Saved", f"{filename} saved successfully.", QSystemTrayIcon.MessageIcon.Information, 2000)

    def open_in_explorer(self, item):
        filepath = item.data(Qt.ItemDataRole.UserRole)
        if filepath and os.path.exists(filepath):
            filepath = os.path.normpath(filepath)
            subprocess.Popen(f'explorer /select,"{filepath}"')

    @pyqtSlot(str)
    def on_error(self, err):
        self.status_label.setText(f"Error: {err}")
        InfoBar.error("Screenshot Error", err, duration=3000, parent=self)

    def closeEvent(self, event):
        self.engine.is_running = False
        self.engine.wait()
        super().closeEvent(event)


class SettingsInterface(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingsInterface")
        self.engine = engine
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.main_layout.setSpacing(24)

        self.title_label = TitleLabel("Application Settings", self)
        self.main_layout.addWidget(self.title_label)

        # File Format Selection
        self.format_group = CardWidget(self)
        self.format_layout = QHBoxLayout(self.format_group)
        
        self.format_icon = ToolButton(FluentIcon.PHOTO, self.format_group)
        self.format_text_layout = QVBoxLayout()
        self.format_title = BodyLabel("Image Format", self.format_group)
        self.format_desc = BodyLabel("Select the file format for your screenshots", self.format_group)
        self.format_desc.setStyleSheet("color: rgba(0, 0, 0, 0.6); font-size: 12px;")
        self.format_text_layout.addWidget(self.format_title)
        self.format_text_layout.addWidget(self.format_desc)
        
        self.format_combo = ComboBox(self.format_group)
        self.format_combo.addItems(["PNG", "JPEG"])
        self.format_combo.setCurrentText(self.engine.format if self.engine.format == "PNG" else "JPEG")
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        
        self.format_layout.addWidget(self.format_icon)
        self.format_layout.addLayout(self.format_text_layout)
        self.format_layout.addStretch(1)
        self.format_layout.addWidget(self.format_combo)
        
        self.main_layout.addWidget(self.format_group)

        # Resolution Selection
        self.res_group = CardWidget(self)
        self.res_layout = QHBoxLayout(self.res_group)
        
        self.res_icon = ToolButton(FluentIcon.TILES, self.res_group)
        self.res_text_layout = QVBoxLayout()
        self.res_title = BodyLabel("Capture Resolution", self.res_group)
        self.res_desc = BodyLabel("Choose output resolution (resizes if different from screen)", self.res_group)
        self.res_desc.setStyleSheet("color: rgba(0, 0, 0, 0.6); font-size: 12px;")
        self.res_text_layout.addWidget(self.res_title)
        self.res_text_layout.addWidget(self.res_desc)
        
        self.res_combo = ComboBox(self.res_group)
        self.res_combo.addItems(["Current Resolution", "1080p", "1440p", "4k", "5k"])
        self.res_combo.setCurrentText(self.engine.resolution_override)
        self.res_combo.currentTextChanged.connect(self.on_resolution_changed)
        
        self.res_layout.addWidget(self.res_icon)
        self.res_layout.addLayout(self.res_text_layout)
        self.res_layout.addStretch(1)
        self.res_layout.addWidget(self.res_combo)
        
        self.main_layout.addWidget(self.res_group)

        # System Info
        self.info_card = CardWidget(self)
        self.info_layout = QVBoxLayout(self.info_card)
        self.res_info_title = SubtitleLabel("System Information", self.info_card)
        self.res_info_card = BodyLabel(f"Detected Desktop Resolution: {self.engine.resolution}", self.info_card)
        self.info_layout.addWidget(self.res_info_title)
        self.info_layout.addWidget(self.res_info_card)
        
        self.main_layout.addWidget(self.info_card)
        self.main_layout.addStretch(1)

    def on_format_changed(self, text):
        self.engine.format = text
        InfoBar.success("Settings Saved", f"Screenshot format changed to {self.engine.format}", duration=2000, parent=self)

    def on_resolution_changed(self, text):
        self.engine.resolution_override = text
        InfoBar.success("Settings Saved", f"Capture resolution set to {text}", duration=2000, parent=self)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screenshot App")
        self.resize(950, 750)
        
        self.screenshot_interface = ScreenshotInterface(self)
        self.settings_interface = SettingsInterface(self.screenshot_interface.engine, self)
        
        self.addSubInterface(self.screenshot_interface, FluentIcon.CAMERA, "Screenshots")
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, "Settings")

if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())
