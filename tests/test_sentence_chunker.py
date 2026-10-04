"""Unit tests for adaptive sentence chunker (TTFA optimizer)."""

import pytest
import asyncio
from pipeline.chunker import SentenceChunker

@pytest.mark.asyncio
async def test_sentence_chunker_punctuation_boundaries():
    """Verify streamed tokens are cleanly segmented on punctuation marks."""
    chunker = SentenceChunker(min_sentence_words=2)

    # Simulated token stream as would arrive from LLM
    tokens = [
        "Your ", "CPU ", "is ", "at ", "14 ", "percent. ",
        "RAM ", "is ", "at ", "58 ", "percent. ",
        "Everything ", "looks ", "great!"
    ]

    async def token_gen():
        for tok in tokens:
            yield tok

    chunks = []
    async for sentence in chunker.chunk_stream(token_gen()):
        chunks.append(sentence)

    assert len(chunks) == 3
    assert chunks[0] == "Your CPU is at 14 percent."
    assert chunks[1] == "RAM is at 58 percent."
    assert chunks[2] == "Everything looks great!"

@pytest.mark.asyncio
async def test_sentence_chunker_flushes_remainder():
    """Verify remainder without trailing punctuation is properly yielded."""
    chunker = SentenceChunker(min_sentence_words=1)

    tokens = ["Hello ", "world, ", "this ", "is ", "ApexCore"]

    async def token_gen():
        for tok in tokens:
            yield tok

    chunks = []
    async for sentence in chunker.chunk_stream(token_gen()):
        chunks.append(sentence)

    assert len(chunks) == 1
    assert chunks[0] == "Hello world, this is ApexCore"
