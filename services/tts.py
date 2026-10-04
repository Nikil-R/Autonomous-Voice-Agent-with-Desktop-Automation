import re
import io
import asyncio
import edge_tts
import sounddevice as sd
import soundfile as sf
import numpy as np
from typing import Optional, Callable
from core.config import TTS_VOICE

def clean_text_for_speech(text: str) -> str:
    """
    Cleans text before voice synthesis to prevent TTS from reading out
    formatting symbols like asterisks, hashtags, backticks, underscores, or bullet dashes.
    Converts numbers and symbols into natural human speech.
    """
    if not text:
        return ""
    
    # 1. Convert mathematical operations into natural spoken English
    # Examples: "20 * 10" -> "20 times 10", "500 + 250" -> "500 plus 250"
    cleaned = re.sub(r'(\d+)\s*\*\s*(\d+)', r'\1 times \2', text)
    cleaned = re.sub(r'(\d+)\s*x\s*(\d+)', r'\1 times \2', cleaned)
    cleaned = re.sub(r'(\d+)\s*\+\s*(\d+)', r'\1 plus \2', cleaned)
    cleaned = re.sub(r'(\d+)\s*-\s*(\d+)', r'\1 minus \2', cleaned)
    cleaned = re.sub(r'(\d+)\s*/\s*(\d+)', r'\1 divided by \2', cleaned)
    cleaned = re.sub(r'(\d+)\s*=\s*(\d+)', r'\1 equals \2', cleaned)

    # 2. Strip markdown headers (###), bold/italic asterisks (***, **, *), underscores (_), backticks (`)
    cleaned = re.sub(r'[*_#`~]', '', cleaned)
    # Strip markdown table formatting bars
    cleaned = re.sub(r'\|', ' ', cleaned)
    # Replace dashes at start of lines (bullet points)
    cleaned = re.sub(r'^\s*[-+]\s+', '', cleaned, flags=re.MULTILINE)
    # Convert % to 'percent'
    cleaned = re.sub(r'(\d+)\s*%', r'\1 percent', cleaned)
    # Clean up multi-spaces and trailing whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

class TTSService:
    """
    Asynchronous streaming neural TTS service using Edge-TTS over WebSockets.
    Decodes compressed audio chunks in memory and outputs to speakers or audio queues.
    """

    def __init__(self, voice: str = TTS_VOICE):
        self.voice = voice

    async def synthesize_to_bytes(self, text: str) -> bytes:
        """Synthesizes text into MP3 audio bytes in memory after sanitizing markdown symbols."""
        clean_prompt = clean_text_for_speech(text)
        if not clean_prompt:
            return b""
        communicate = edge_tts.Communicate(clean_prompt, self.voice)
        audio_buffer = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.extend(chunk["data"])
        return bytes(audio_buffer)

    async def stream_audio_chunks(self, text: str):
        """
        Synthesizes text and yields binary MP3 audio frames incrementally
        as soon as Edge-TTS generates them for sub-300ms Time-to-First-Audio (TTFA).
        """
        clean_prompt = clean_text_for_speech(text)
        if not clean_prompt:
            return
        communicate = edge_tts.Communicate(clean_prompt, self.voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk["data"]:
                yield chunk["data"]

    @staticmethod
    def decode_audio_bytes(audio_bytes: bytes):
        """Decodes MP3/WAV audio bytes into (numpy_data, sample_rate)."""
        buffer = io.BytesIO(audio_bytes)
        data, sample_rate = sf.read(buffer)
        return data, sample_rate

    async def play_audio_stream(
        self,
        audio_bytes: bytes,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Plays audio in non-blocking slices with millisecond barge-in cancellation.
        Returns True if played completely, False if interrupted.
        """
        if not audio_bytes:
            return True

        data, sample_rate = self.decode_audio_bytes(audio_bytes)
        # Ensure 2D (samples, channels)
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        block_size = int(sample_rate * 0.05)  # 50ms playback chunk
        total_samples = len(data)
        current_idx = 0

        # Run non-blocking OutputStream
        with sd.OutputStream(samplerate=sample_rate, channels=data.shape[1], dtype=data.dtype) as stream:
            while current_idx < total_samples:
                # Check for Barge-in interruption
                if stop_check and stop_check():
                    return False

                end_idx = min(current_idx + block_size, total_samples)
                slice_data = data[current_idx:end_idx]
                stream.write(slice_data)
                current_idx = end_idx
                # Yield control to event loop
                await asyncio.sleep(0.001)

        return True
