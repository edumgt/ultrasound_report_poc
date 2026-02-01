from __future__ import annotations
import os
import queue
import numpy as np

from PySide6.QtCore import QThread, Signal, QObject, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QTextEdit, QPushButton, QLabel, QVBoxLayout, QWidget,
    QHBoxLayout, QMessageBox
)

# SAFE_MODE=1이면 STT/오디오 없이 UI만 띄워 네이티브 크래시 원인을 분리합니다.
SAFE_MODE = os.environ.get("SAFE_MODE", "0") == "1"

if not SAFE_MODE:
    from core.audio_capture import AudioCapture
    from core.term_correction import TermCorrector
    from core.structuring import Structurer
    from core.report_template import ReportRenderer
    from core.storage import save_session


class Worker(QObject):
    partial = Signal(str, list)   # (corrected_text, changes)
    status = Signal(str)
    error = Signal(str)

    def __init__(self, audio_q: "queue.Queue[np.ndarray]", stt, corrector, sample_rate: int = 16000):
        super().__init__()
        self.audio_q = audio_q
        self.stt = stt
        self.corrector = corrector
        self.sample_rate = sample_rate
        self.running = False

    def run(self):
        self.running = True
        self.status.emit("Listening...")
        buffer = []

        while self.running:
            try:
                chunk = self.audio_q.get(timeout=0.2)
                buffer.append(chunk)

                if sum(len(x) for x in buffer) >= int(self.sample_rate * 1.5):
                    audio = np.concatenate(buffer).astype(np.float32)
                    buffer.clear()

                    text = self.stt.transcribe(audio, self.sample_rate)
                    if text:
                        corrected, changes = self.corrector.correct(text)
                        self.partial.emit(corrected, changes)

            except queue.Empty:
                pass
            except Exception as e:
                self.error.emit(str(e))

        self.status.emit("Stopped.")

    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    # -------- SAFE MODE UI --------
    def _setup_ui_safe_only(self):
        self.setWindowTitle("Ultrasound Auto Report PoC (SAFE_MODE)")
        self.status_label = QLabel("SAFE_MODE=1 (UI only)")
        self.status_label.setAlignment(Qt.AlignLeft)

        self.text_live = QTextEdit()
        self.text_live.setReadOnly(True)
        self.text_live.setPlaceholderText("SAFE MODE: STT/Audio disabled. Close with Esc.")

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.text_live)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)

    def _setup_shortcuts_safe_only(self):
        QShortcut(QKeySequence("Esc"), self, activated=self.close)

    # -------- NORMAL MODE --------
    def __init__(self, assets_dir: str, sessions_dir: str):
        super().__init__()
        self.assets_dir = assets_dir
        self.sessions_dir = sessions_dir

        if SAFE_MODE:
            self._setup_ui_safe_only()
            self._setup_shortcuts_safe_only()
            return

        self.setWindowTitle("Ultrasound Auto Report PoC")
        self.audio_q: "queue.Queue[np.ndarray]" = queue.Queue()

        self.corrector, categories = TermCorrector.load(os.path.join(self.assets_dir, "terms.json"))
        self.structurer = Structurer(categories, key_to_canonical=self.corrector.key_to_canonical)
        self.renderer = ReportRenderer(os.path.join(self.assets_dir, "templates"))

        prompt = self._build_prompt()
        self._stt_cfg = dict(
            model_size="tiny",
            device="cpu",
            compute_type="int8",
            beam_size=1,
            vad_filter=False,
            initial_prompt=prompt
        )
        self.stt = None

        self.capture = AudioCapture(self.audio_q, sample_rate=16000, block_ms=500)
        self.worker = None
        self.thread = None

        self._setup_ui()
        self._setup_shortcuts()

        self.raw_text_accum = ""
        self.corrected_text_accum = ""
        self.last_report = ""

    def _build_prompt(self) -> str:
        ex_path = os.path.join(self.assets_dir, "examples.txt")
        examples = ""
        if os.path.exists(ex_path):
            with open(ex_path, "r", encoding="utf-8") as f:
                examples = f.read().strip()

        return (
            "You are transcribing an ultrasound medical dictation.\n"
            "Korean and English mixed medical terms must be written in correct English spelling.\n"
            f"{examples}\n"
        )

    def _setup_ui(self):
        self.status_label = QLabel("Idle")
        self.status_label.setAlignment(Qt.AlignLeft)

        self.text_live = QTextEdit()
        self.text_live.setReadOnly(True)
        self.text_live.setPlaceholderText("실시간 인식/보정 결과(누적)")

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("사용자 수정 에디터(최종 리포트 생성 기준)")

        self.btn_toggle = QPushButton("Start/Stop (F2)")
        self.btn_reset = QPushButton("Reset (F3)")
        self.btn_report = QPushButton("Generate Report (Ctrl+Enter)")
        self.btn_save = QPushButton("Save Session (Ctrl+S)")

        self.btn_toggle.clicked.connect(self.toggle)
        self.btn_reset.clicked.connect(self.reset)
        self.btn_report.clicked.connect(self.generate_report)
        self.btn_save.clicked.connect(self.save)

        top = QHBoxLayout()
        top.addWidget(self.btn_toggle)
        top.addWidget(self.btn_reset)
        top.addWidget(self.btn_report)
        top.addWidget(self.btn_save)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addLayout(top)
        layout.addWidget(QLabel("Live (Auto-corrected)"))
        layout.addWidget(self.text_live)
        layout.addWidget(QLabel("Editable (Final)"))
        layout.addWidget(self.text_edit)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F2"), self, activated=self.toggle)
        QShortcut(QKeySequence("F3"), self, activated=self.reset)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.generate_report)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save)

    def _ensure_worker(self) -> bool:
        os.environ.setdefault("CT2_FORCE_CPU_ISA", "GENERIC")

        if self.stt is None:
            try:
                print("[ui] loading STT model...", flush=True)
                self.on_status("Loading STT model... (first run may download)")
                from core.stt_whisper import WhisperSTT, STTConfig
                cfg = STTConfig(**self._stt_cfg)
                self.stt = WhisperSTT(cfg)
                print("[ui] STT model loaded", flush=True)
            except Exception as e:
                self.on_error("Failed to load STT model:\n" + str(e))
                self.on_status("STT load failed.")
                self.stt = None
                return False

        if self.thread is None or (hasattr(self.thread, "isRunning") and not self.thread.isRunning()):
            self.worker = Worker(self.audio_q, self.stt, self.corrector)
            self.thread = QThread()
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.partial.connect(self.on_partial)
            self.worker.status.connect(self.on_status)
            self.worker.error.connect(self.on_error)
        return True

    def toggle(self):
        if self.thread and self.thread.isRunning():
            self.stop()
        else:
            self.start()

    def start(self):
        if not self._ensure_worker():
            return
        self.capture.start()
        self.thread.start()
        self.on_status("Started.")

    def stop(self):
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
        self.capture.stop()

    def reset(self):
        self.stop()
        self.capture.reset()
        self.text_live.clear()
        self.text_edit.clear()
        self.raw_text_accum = ""
        self.corrected_text_accum = ""
        self.last_report = ""
        self.on_status("Reset.")

    def on_partial(self, corrected: str, changes: list):
        self.corrected_text_accum += corrected + "\n"
        self.text_live.append(corrected)
        self.text_edit.append(corrected)

    def on_status(self, s: str):
        self.status_label.setText(s)

    def on_error(self, msg: str):
        QMessageBox.critical(self, "Error", msg)

    def generate_report(self):
        final_text = self.text_edit.toPlainText().strip()
        if not final_text:
            self.on_status("No text to report.")
            return
        structured = self.structurer.extract(final_text)
        report = self.renderer.render(structured=structured, cleaned_text=final_text)
        self.last_report = report
        self.text_live.append("\n--- [REPORT] ---\n" + report + "\n--- [/REPORT] ---\n")
        self.on_status("Report generated.")

    def save(self):
        final_text = self.text_edit.toPlainText().strip()
        if not final_text:
            self.on_status("Nothing to save.")
            return
        structured = self.structurer.extract(final_text)
        report = self.last_report or self.renderer.render(structured=structured, cleaned_text=final_text)
        folder = save_session(
            base_dir=self.sessions_dir,
            raw_text=self.raw_text_accum,
            corrected_text=final_text,
            report_text=report,
            structured=structured
        )
        self.on_status(f"Saved session: {folder}")

    def closeEvent(self, event):
        if not SAFE_MODE:
            self.stop()
        super().closeEvent(event)
