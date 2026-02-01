import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt

print("[qt_min] start", flush=True)
app = QApplication(sys.argv)
w = QMainWindow()
w.setWindowTitle("qt_min")
lab = QLabel("Qt minimal window", alignment=Qt.AlignCenter)
w.setCentralWidget(lab)
w.resize(480, 240)
w.show()
print("[qt_min] shown", flush=True)
sys.exit(app.exec())
