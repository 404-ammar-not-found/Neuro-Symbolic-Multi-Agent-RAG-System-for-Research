import unittest

from src.pdf_parsing.text_chunker import TextChunker


class TextChunkerTests(unittest.TestCase):
    def test_split_basic(self):
        chunker = TextChunker(chunk_size=5, chunk_overlap=0)
        chunks = chunker.split("abcdefghijkl")
        self.assertEqual(chunks, ["abcde", "fghij", "kl"])

    def test_split_with_overlap(self):
        chunker = TextChunker(chunk_size=4, chunk_overlap=1)
        chunks = chunker.split("abcdefg")
        self.assertEqual(chunks, ["abcd", "defg"])

    def test_split_stream(self):
        chunker = TextChunker(chunk_size=4, chunk_overlap=1)
        segments = ["ab", "cdef", "gh"]
        chunks = list(chunker.split_stream(segments))
        self.assertEqual(chunks, ["abcd", "defg", "gh"])

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            TextChunker(chunk_size=0)
        with self.assertRaises(ValueError):
            TextChunker(chunk_size=10, chunk_overlap=10)


if __name__ == "__main__":
    unittest.main()
