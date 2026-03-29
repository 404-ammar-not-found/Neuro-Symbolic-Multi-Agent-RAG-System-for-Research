from dataclasses import dataclass
from typing import Iterable


@dataclass
class TextChunker:
    """Split text into fixed-size chunks with optional overlap."""

    chunk_size: int = 1000
    chunk_overlap: int = 200

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("chunk_overlap must be in [0, chunk_size).")

    def split(self, text: str) -> list[str]:
        """Split a single text string into chunks."""

        chunks: list[str] = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunks.append(text[start:end])
            start = end - self.chunk_overlap
        return chunks

    def split_many(self, texts: Iterable[str]) -> list[str]:
        """Split multiple text strings and flatten the resulting chunks."""

        aggregated: list[str] = []
        for text in texts:
            aggregated.extend(self.split(text))
        return aggregated

    def split_stream(self, segments: Iterable[str]):
        """Yield chunks incrementally from an iterable of text segments."""

        buffer = ""
        for segment in segments:
            buffer += segment
            while len(buffer) >= self.chunk_size:
                chunk = buffer[: self.chunk_size]
                yield chunk
                buffer = buffer[self.chunk_size - self.chunk_overlap :]

        if buffer:
            yield buffer