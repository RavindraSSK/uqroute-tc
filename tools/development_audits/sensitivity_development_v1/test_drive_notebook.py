"""Mock Drive input reuse and completed-run protection, without network access."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile


REPO = Path(__file__).resolve().parents[3]


class DriveNotebookTests(unittest.TestCase):
    def test_hash_checked_reuse_export_and_cross_runtime_dispatch_guard(self):
        nb = json.loads((REPO / "notebooks" /
            "UQRoute_TC_Sensitivity_Development_Google_Drive_v1.ipynb").read_bytes())
        source = lambda i: "".join(nb["cells"][i]["source"])
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cloud = base / "drive"
            inputs = cloud / "MyDrive/UQRoute_TC/sensitivity_inputs"
            inputs.mkdir(parents=True)
            pins = {}
            sha = lambda b: hashlib.sha256(b).hexdigest()
            for model in ("qwen15b", "llama3b", "qwen7b"):
                path = inputs / (model + "_sensitivity_development_transfer_v1.zip")
                manifest = (model + " fixture manifest").encode()
                with zipfile.ZipFile(path, "w") as z:
                    z.writestr("manifest.json", manifest)
                    z.writestr("requests.json", b"[]")
                pins[model] = (sha(path.read_bytes()), sha(manifest))
            google = types.ModuleType("google")
            colab = types.ModuleType("google.colab")
            google.colab = colab
            colab.drive = types.SimpleNamespace(mount=lambda path: None)
            code = source(2).replace("/content/drive", str(cloud)).replace(
                "/content/uqroute_sensitivity_development_v1", str(base / "runtime"))
            code = "\n".join("PINS = " + repr(pins) if line.startswith("PINS = ")
                             else line for line in code.splitlines())
            scope = {}
            with patch.dict(sys.modules, {"google": google, "google.colab": colab}):
                exec(code, scope)
                exec(code, scope)
            root = scope["ROOT"]
            evidence = root / "uqroute_qwen15b_sensitivity_development_fixture.zip"
            with zipfile.ZipFile(evidence, "w") as z:
                z.writestr("fixture.txt", b"evidence")
            dest = scope["persist_archive"](evidence)
            scope["persist_archive"](evidence)
            self.assertEqual(evidence.read_bytes(), dest.read_bytes())
            function = next(node for node in ast.parse(source(4)).body
                            if isinstance(node, ast.FunctionDef) and node.name == "run_model")
            ready = root / "setup_complete.json"
            ready.write_text("{}")
            python = root / "python"
            python.touch()
            for name in ("sensitivity_client.py", "runner.py"):
                (root / name).write_text("fixture")
            scope.update(READY=ready, PYTHON=python,
                         CLIENT_SOURCE="fixture", RUNNER_SOURCE="fixture")
            exec(ast.unparse(function), scope)
            with self.assertRaisesRegex(RuntimeError, "Do not generate"):
                scope["run_model"]("qwen15b")
            original = (scope["INBOX"] / scope["NAMES"]["qwen15b"]).read_bytes()
            (inputs / scope["NAMES"]["qwen15b"]).write_bytes(b"changed")
            with patch.dict(sys.modules, {"google": google, "google.colab": colab}):
                with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                    exec(code, {})
            self.assertEqual((scope["INBOX"] / scope["NAMES"]["qwen15b"]).read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
