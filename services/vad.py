"""Silero VAD ONNX Engine Wrapper with recurrent hidden state tracking."""

import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import Union
from core.config import VAD_MODEL_PATH, INPUT_SAMPLE_RATE

class SileroVAD:
    """
    Sub-millisecond neural Voice Activity Detection using Silero VAD v5 ONNX.
    Maintains recurrent hidden states across audio frames.
    """

    def __init__(self, model_path: Union[str, Path] = VAD_MODEL_PATH):
        self.model_path = str(model_path)
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            self.model_path,
            sess_options=opts,
            providers=["CPUExecutionProvider"]
        )
        self.sample_rate = INPUT_SAMPLE_RATE
        self.reset_states()

    def reset_states(self) -> None:
        """Resets the recurrent hidden state tensor (2, 1, 128)."""
        self._state = np.zeros((2, 1, 128), dtype=np.float32)

    def is_speech(self, audio_chunk: np.ndarray, threshold: float = 0.55) -> bool:
        """Returns True if speech probability exceeds threshold."""
        prob = self.process_chunk(audio_chunk)
        return prob >= threshold

    def process_chunk(self, audio_chunk: np.ndarray) -> float:
        """
        Processes a 512-sample audio chunk (float32 or int16 normalized)
        and returns speech probability between 0.0 and 1.0.
        """
        # Convert int16 to float32 [-1.0, 1.0] if necessary
        if audio_chunk.dtype == np.int16:
            audio_data = audio_chunk.astype(np.float32) / 32768.0
        else:
            audio_data = audio_chunk.astype(np.float32)

        if audio_data.ndim == 1:
            input_tensor = audio_data.reshape(1, -1)
        else:
            input_tensor = audio_data

        sr_tensor = np.array(self.sample_rate, dtype=np.int64)

        ort_inputs = {
            "input": input_tensor,
            "state": self._state,
            "sr": sr_tensor
        }

        out, new_state = self.session.run(None, ort_inputs)
        self._state = new_state
        return float(out[0][0])
