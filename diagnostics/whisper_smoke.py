import os, numpy as np
os.environ["CT2_FORCE_CPU_ISA"]="GENERIC"
from faster_whisper import WhisperModel
print("[whisper_smoke] loading tiny", flush=True)
m=WhisperModel("tiny", device="cpu", compute_type="int8")
audio=np.zeros(16000*3, dtype=np.float32)
segs,info=m.transcribe(audio, beam_size=1, vad_filter=False)
print("[whisper_smoke] done", flush=True)
