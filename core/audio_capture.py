from __future__ import annotations
import queue
import numpy as np

class AudioCapture:
    """
    Microphone capture using sounddevice, but imported lazily inside start()
    to reduce startup failures.
    """
    def __init__(self, out_queue: "queue.Queue[np.ndarray]", sample_rate: int = 16000, block_ms: int = 500):
        self.q = out_queue
        self.sample_rate = sample_rate
        self.blocksize = int(sample_rate * (block_ms / 1000))
        self.stream = None
        self._running = False

    def start(self):
        if self._running:
            return
        import sounddevice as sd

        self._running = True
        self.stream = sd.InputStream(
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.blocksize,
            dtype="float32",
            callback=self._callback
        )
        self.stream.start()

    def stop(self):
        self._running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def reset(self):
        try:
            while True:
                self.q.get_nowait()
        except queue.Empty:
            pass

    def _callback(self, indata, frames, time, status):
        if not self._running:
            return
        audio = np.squeeze(indata.copy())
        self.q.put(audio)
