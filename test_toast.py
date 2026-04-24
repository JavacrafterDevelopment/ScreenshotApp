import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QWidget
from PyQt6.QtGui import QIcon
from qfluentwidgets import FluentIcon

app = QApplication(sys.argv)
tray = QSystemTrayIcon()
tray.setIcon(FluentIcon.CAMERA.icon())
tray.show()
tray.showMessage("Screenshot App", "This is a test notification!", QSystemTrayIcon.MessageIcon.Information, 2000)

QTimer = __import__('PyQt6.QtCore').QtCore.QTimer
QTimer.singleShot(3000, app.quit)

sys.exit(app.exec())
