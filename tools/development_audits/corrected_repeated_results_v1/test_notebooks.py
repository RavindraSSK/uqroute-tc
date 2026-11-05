"""Offline notebook validation and upload recovery regression checks."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[3]
NAMES = [
    "Qwen15B_Corrected_Repeated", "Llama3B_Corrected_Repeated",
    "Qwen7B_Corrected_Repeated", "Sensitivity_Development_Three_Models",
    "Sensitivity_Development_Google_Drive",
]


def notebook(key):
    return json.loads((REPO / "notebooks" / f"UQRoute_TC_{key}_v1.ipynb").read_bytes())


class NotebookTests(unittest.TestCase):
    def test_code_and_embedded_execution_sources_compile(self):
        for name in NAMES:
            with self.subTest(notebook=name):
                for cell in notebook(name)["cells"]:
                    if cell["cell_type"] != "code":
                        continue
                    self.assertEqual(cell["outputs"], [])
                    self.assertIsNone(cell["execution_count"])
                    tree = ast.parse("".join(cell["source"]))
                    compile(tree, name, "exec")
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                            if any(isinstance(t, ast.Name) and t.id in
                                   {"CLIENT_SOURCE", "RUNNER_SOURCE"} for t in node.targets):
                                compile(node.value.value, name + " embedded source", "exec")

    def upload(self, name, auto_saved, existing=b"", uploaded=b"approved", count=1):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "input.zip"
            if existing:
                target.write_bytes(existing)
            raw = b"approved"
            cell = "".join(notebook(name)["cells"][2]["source"])
            lines = []
            for line in cell.splitlines():
                if line.startswith("expected = "):
                    line = "expected = " + repr(hashlib.sha256(raw).hexdigest())
                elif line.startswith("target = "):
                    line = "target = Path(" + repr(str(target)) + ")"
                lines.append(line)
            calls = []

            def upload():
                calls.append(True)
                if auto_saved:
                    target.write_bytes(uploaded)
                return {f"input-{i}.zip": uploaded for i in range(count)}

            google = types.ModuleType("google")
            colab = types.ModuleType("google.colab")
            google.colab = colab
            colab.files = types.SimpleNamespace(upload=upload)
            with patch.dict(sys.modules, {"google": google, "google.colab": colab}):
                exec("\n".join(lines), {})
            self.assertEqual(target.read_bytes(), raw)
            return len(calls)

    def test_auto_saved_upload_is_reused(self):
        # Colab writes the upload to disk before returning its bytes.
        for name in NAMES[:3]:
            with self.subTest(notebook=name):
                self.assertEqual(self.upload(name, auto_saved=True), 1)

    def test_existing_verified_file_skips_upload(self):
        for name in NAMES[:3]:
            with self.subTest(notebook=name):
                self.assertEqual(self.upload(name, auto_saved=False, existing=b"approved"), 0)

    def test_changed_existing_input_is_preserved(self):
        with self.assertRaisesRegex(RuntimeError, "Canonical input differs"):
            self.upload(NAMES[0], auto_saved=False, existing=b"other")

    def test_wrong_bytes_and_multiple_uploads_fail(self):
        with self.assertRaisesRegex(RuntimeError, "Wrong transfer"):
            self.upload(NAMES[0], auto_saved=True, uploaded=b"other")
        with self.assertRaisesRegex(RuntimeError, "one INPUT"):
            self.upload(NAMES[0], auto_saved=False, count=2)


if __name__ == "__main__":
    unittest.main()
