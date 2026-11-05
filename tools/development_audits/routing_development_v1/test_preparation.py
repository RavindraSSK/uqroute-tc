"""Request comparison and plan construction tests, using artificial records."""

import copy
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "fallback_preparation", Path(__file__).with_name("prepare_fallback.py")
)
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


def rows(model):
    return [
        {
            "case_key": f"fixture-{i}",
            "canonical_base_id": f"group-{i // 12}",
            "source_file": "fixture.jsonl",
            "benchmark": "fixture",
            "request": {
                "model": model,
                "messages": [{"role": "user", "content": "fixture"}],
                "temperature": 0.001,
                "max_tokens": 1024,
            },
        }
        for i in range(1728)
    ]


class PreparationTests(unittest.TestCase):
    def fake_workflow(self, bad_model=False):
        previous = rows("small")

        def prepare(
            repo, audit, denominators, candidate_pin, denominator_pin, model, selection, path
        ):
            self.assertEqual(
                (candidate_pin, denominator_pin), (preparation.CANDIDATES, preparation.DENOMINATORS)
            )
            self.assertEqual((model, selection), ("qwen14b_awq", "full-development"))
            path.mkdir()
            manifest = {
                "model_settings": {
                    "role": "fallback",
                    "model_id": preparation.MODEL,
                    "model_revision": preparation.REVISION,
                    "tokenizer_revision": preparation.REVISION,
                    "dtype": "float16",
                    "quantization": "AWQ 4-bit checkpoint",
                }
            }
            if bad_model:
                manifest["model_settings"]["model_revision"] = "wrong"
            raw = json.dumps(manifest).encode()
            (path / "manifest.json").write_bytes(raw)
            (path / "requests.json").write_text(json.dumps(rows(preparation.MODEL)))
            return {"manifest_sha256": preparation.sha(raw)}

        def load_plan(repo, path, pin):
            if path == repo / preparation.PREVIOUS:
                self.assertEqual(pin, preparation.PREVIOUS_MANIFEST)
                return {}, previous
            return (
                json.loads((path / "manifest.json").read_bytes()),
                json.loads((path / "requests.json").read_bytes()),
            )

        return SimpleNamespace(prepare=prepare, load_plan=load_plan)

    def test_packages_fresh_plan_and_rejects_second_run_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            fake = self.fake_workflow()
            with (
                patch.object(preparation, "load_workflow", return_value=fake),
                patch.object(
                    preparation.subprocess, "run", return_value=SimpleNamespace(returncode=0)
                ),
            ):
                result = preparation.run(repo)
                output = repo / preparation.OUTPUT
                archive = output / result["transfer_file"]
                self.assertEqual(preparation.sha(archive.read_bytes()), result["transfer_sha256"])
                with zipfile.ZipFile(archive) as z:
                    self.assertEqual(set(z.namelist()), {"manifest.json", "requests.json"})
                    self.assertEqual(len(json.loads(z.read("requests.json"))), 1728)
                self.assertEqual(result["generation_requests_sent"], 0)
                self.assertFalse(result["held_out_access_enabled"])
                self.assertFalse(result["dispatch_authorized_by_preparation"])
                saved = archive.read_bytes()
                with self.assertRaisesRegex(ValueError, "preserve"):
                    preparation.run(repo)
                self.assertEqual(archive.read_bytes(), saved)

    def test_bad_prepared_model_cannot_publish_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            fake = self.fake_workflow(bad_model=True)
            with (
                patch.object(preparation, "load_workflow", return_value=fake),
                patch.object(
                    preparation.subprocess, "run", return_value=SimpleNamespace(returncode=0)
                ),
            ):
                with self.assertRaisesRegex(ValueError, "settings differ"):
                    preparation.run(repo)
            self.assertFalse((repo / preparation.OUTPUT).exists())

    def test_only_model_changes_and_sources_are_not_modified(self):
        new, old = rows(preparation.MODEL), rows("small")
        preserved = copy.deepcopy((new, old))
        preparation.validate_matching_requests(new, old)
        self.assertEqual((new, old), preserved)

    def test_case_loss_duplicate_or_order_change_rejected(self):
        for change in ("missing", "duplicate", "order"):
            new, old = rows(preparation.MODEL), rows("small")
            if change == "missing":
                new.pop()
            elif change == "duplicate":
                new[0] = new[1]
            else:
                new.reverse()
            with self.subTest(change=change), self.assertRaises(ValueError):
                preparation.validate_matching_requests(new, old)

    def test_prompt_settings_lineage_and_model_changes_rejected(self):
        for change in ("prompt", "settings", "lineage", "model"):
            new, old = rows(preparation.MODEL), rows("small")
            if change == "prompt":
                new[0]["request"]["messages"][0]["content"] = "different"
            elif change == "settings":
                new[0]["request"]["temperature"] = 0.7
            elif change == "lineage":
                new[0]["canonical_base_id"] = "different"
            else:
                new[0]["request"]["model"] = "different"
            with self.subTest(change=change), self.assertRaises(ValueError):
                preparation.validate_matching_requests(new, old)


if __name__ == "__main__":
    unittest.main()
