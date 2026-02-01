from __future__ import annotations
import sys, os, traceback

print("[app] starting...", flush=True)

from PySide6.QtWidgets import QApplication
print("[app] Qt imported", flush=True)

from ui.main_window import MainWindow
print("[app] MainWindow imported", flush=True)

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SESSIONS_DIR = os.path.join(BASE_DIR, "data", "sessions")

def main():
    try:
        app = QApplication(sys.argv)
        print("[app] QApplication created", flush=True)
        win = MainWindow(assets_dir=ASSETS_DIR, sessions_dir=SESSIONS_DIR)
        print("[app] MainWindow created", flush=True)
        win.resize(1000, 900)
        win.show()
        print("[app] window shown; entering event loop", flush=True)
        sys.exit(app.exec())
    except Exception:
        print("FATAL: app crashed during startup", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
