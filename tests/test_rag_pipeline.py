import sys
import types
import unittest

# Provide minimal stubs for optional third-party modules to allow import in tests.
if "google" not in sys.modules:
    sys.modules["google"] = types.SimpleNamespace(genai=types.SimpleNamespace())
if "google.genai" not in sys.modules:
    sys.modules["google.genai"] = sys.modules["google"].genai
if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)
if "fitz" not in sys.modules:
    sys.modules["fitz"] = types.SimpleNamespace()

from src.pipeline.rag_pipeline import build_context


class BuildContextTests(unittest.TestCase):
    def test_build_context_contains_ids_and_docs(self):
        matches = [
            {
                "metadata": {"source": "file.pdf", "chunk_index": 1},
                "document": "example text",
            }
        ]
        context = build_context(matches)
        self.assertIn("[file.pdf#chunk1]", context)
        self.assertIn("example text", context)


if __name__ == "__main__":
    unittest.main()
