from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
import numpy as np
from faster_whisper import WhisperModel

@dataclass
class STTConfig:
    model_size: str = "tiny"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 1
    vad_filter: bool = False
    language: Optional[str] = None
    initial_prompt: str = ""

class WhisperSTT:
    def __init__(self, cfg: STTConfig):
        self.cfg = cfg
        self.model = WhisperModel(cfg.model_size, device=cfg.device, compute_type=cfg.compute_type)

    def transcribe(self, audio_f32: np.ndarray, sample_rate: int) -> str:
        segments, _info = self.model.transcribe(
            audio_f32,
            language=self.cfg.language,
            beam_size=self.cfg.beam_size,
            vad_filter=self.cfg.vad_filter,
            initial_prompt=self.cfg.initial_prompt
        )
        parts: List[str] = []
        for seg in segments:
            if seg.text:
                parts.append(seg.text.strip())
        return " ".join(parts).strip()
