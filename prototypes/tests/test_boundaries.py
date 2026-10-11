"""Prototypes map into the vocab. They do not read the answer key or the harness."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BoundaryTest(unittest.TestCase):
    def test_prototypes_do_not_import_harness_or_labels(self):
        for path in (ROOT / "prototypes").rglob("*.py"):
            if path.name == "test_boundaries.py":
                continue
            text = path.read_text()
            tree = ast.parse(text)
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                for module in modules:
                    self.assertNotEqual(module.split(".")[0], "harness", f"{path} imports {module}")
            self.assertNotIn("score_spec", text, path)
            self.assertNotIn("exam/labels", text, path)
            self.assertNotIn("labels/", text, path)


if __name__ == "__main__":
    unittest.main()
