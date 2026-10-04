"""Adaptive sentence boundary chunker for sub-500ms TTFA."""

import re
from typing import AsyncGenerator

class SentenceChunker:
    """
    Buffers a stream of incoming tokens and yields complete sentences immediately
    upon encountering punctuation boundaries (. ? ! ; : \n).
    
    This enables Sentence #1 to be sent to TTS synthesis while the LLM is still
    generating Sentence #2, drastically reducing Time-to-First-Audio (TTFA).
    """

    PUNCTUATION_REGEX = re.compile(r"([.?!;:\n]+(?:\s+|$))")

    def __init__(self, min_sentence_words: int = 3):
        self.min_sentence_words = min_sentence_words
        self._buffer: str = ""

    async def chunk_stream(self, token_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """
        Consumes tokens and yields punctuated sentences as soon as they form.
        """
        self._buffer = ""
        
        async for token in token_stream:
            self._buffer += token
            
            # Check for sentence split
            parts = self.PUNCTUATION_REGEX.split(self._buffer)
            if len(parts) > 1:
                # We have at least one complete sentence + remaining buffer
                sentence = (parts[0] + parts[1]).strip()
                # Check if sentence meets minimum word count or has substantive content
                if len(sentence.split()) >= self.min_sentence_words or len(parts) > 3:
                    yield sentence
                    self._buffer = "".join(parts[2:])
                else:
                    # Keep accumulating if too short (e.g., abbreviations like "Dr." or "1.")
                    pass

        # Flush any remaining text in buffer
        remainder = self._buffer.strip()
        if remainder:
            yield remainder
            self._buffer = ""
