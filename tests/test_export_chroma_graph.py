import importlib.util
import sys
import types
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "export_chroma_graph.py"


def load_module():
    if "chromadb" not in sys.modules:
        # Minimal stub so module import succeeds without installing chromadb
        stub = types.SimpleNamespace(PersistentClient=lambda *args, **kwargs: None)
        sys.modules["chromadb"] = stub
    spec = importlib.util.spec_from_file_location("export_chroma_graph", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class MergeGraphsTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_merge_adds_missing_nodes_and_links(self):
        existing = {
            "nodes": [{"id": "a"}],
            "links": [{"source": "a", "target": "b", "type": "sequence"}],
        }
        fresh = {
            "nodes": [{"id": "b"}],
            "links": [
                {"source": "a", "target": "b", "type": "sequence"},
                {"source": "b", "target": "c", "type": "similarity"},
            ],
        }

        merged = self.module.merge_graphs(existing, fresh)

        self.assertEqual({n["id"] for n in merged["nodes"]}, {"a", "b"})
        self.assertIn({"source": "b", "target": "c", "type": "similarity"}, merged["links"])

    def test_merge_backfills_link_type(self):
        existing = {
            "nodes": [{"id": "a"}],
            "links": [{"source": "a", "target": "b"}],
        }
        fresh = {"nodes": [], "links": []}

        merged = self.module.merge_graphs(existing, fresh)

        self.assertEqual(merged["links"][0]["type"], "sequence")


if __name__ == "__main__":
    unittest.main()
