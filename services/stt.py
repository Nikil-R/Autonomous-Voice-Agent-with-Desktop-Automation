"""In-Memory Speech-to-Text transcription via Groq Whisper Large v3 Turbo."""

import io
import wave
import numpy as np
from typing import Union
from groq import AsyncGroq
from core.config import GROQ_API_KEY, GROQ_WHISPER_MODEL, INPUT_SAMPLE_RATE

class WhisperSTTService:
    """
    Zero-disk in-memory audio packaging and ultra-fast transcription service.
    Encodes raw PCM into standard WAV bytes in RAM via io.BytesIO()
    and sends directly to Groq Whisper LPU.
    """

    def __init__(self, api_key: str = GROQ_API_KEY, model: str = GROQ_WHISPER_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = AsyncGroq(api_key=self.api_key)

    @staticmethod
    def pcm_to_wav_bytes(pcm_data: Union[np.ndarray, bytes], sample_rate: int = INPUT_SAMPLE_RATE) -> bytes:
        """
        Converts raw PCM audio array or bytes into standard 16-bit mono WAV in memory.
        """
        if isinstance(pcm_data, np.ndarray):
            if pcm_data.dtype != np.int16:
                # Normalize float to int16
                pcm_data = (np.clip(pcm_data, -1.0, 1.0) * 32767).astype(np.int16)
            raw_bytes = pcm_data.tobytes()
        else:
            raw_bytes = pcm_data

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)      # Mono
            wf.setsampwidth(2)      # 16-bit = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(raw_bytes)

        buffer.seek(0)
        return buffer.read()

    async def transcribe(self, audio_data: Union[np.ndarray, bytes], prompt: str = "") -> str:
        """
        Transcribes audio data in memory using Groq Whisper.
        Returns the transcription string.
        """
        wav_bytes = self.pcm_to_wav_bytes(audio_data)
        
        # Package for Groq files parameter: (filename, bytes, content_type)
        audio_file = ("audio.wav", wav_bytes, "audio/wav")

        response = await self.client.audio.transcriptions.create(
            file=audio_file,
            model=self.model,
            language="en",
            prompt=prompt,
            response_format="json"
        )
        return response.text.strip()
