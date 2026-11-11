"""Safe CPU archive import checks with synthetic files only."""

import io
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

import run_cpu as importer


def packed(names, symlink=False):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        for name in names:
            entry = zipfile.ZipInfo(name)
            if symlink:
                entry.create_system = 3
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(entry, b"fixture")
    return stream.getvalue()


class ImportTests(unittest.TestCase):
    def test_regular_payload_is_not_executed(self):
        self.assertEqual(
            importer.safe_payloads(packed(["metadata/source.py"])),
            {"metadata/source.py": b"fixture"},
        )

    def test_path_aliases_traversal_and_roots_rejected(self):
        names = [
            "../escape",
            "/run/file",
            "run/../escape",
            "run/./file",
            "run//file",
            "run\\file",
            "run/C:stream",
            "other/file",
            "run/trailing.",
            "run/trailing ",
        ]
        for name in names:
            with self.subTest(name=name), self.assertRaises(ValueError):
                importer.safe_payloads(packed([name]))

    def test_case_collision_and_duplicate_rejected(self):
        for names in (["run/A", "run/a"], ["run/A", "run/A"]):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                raw = packed(names)
            with self.assertRaises(ValueError):
                importer.safe_payloads(raw)

    def test_symlink_rejected(self):
        with self.assertRaises(ValueError):
            importer.safe_payloads(packed(["run/link"], symlink=True))

    def test_wrong_outer_hash_rejected_before_unpack(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake.zip"
            path.write_bytes(b"not a ZIP")
            with self.assertRaisesRegex(ValueError, "SHA256 differs"):
                importer.validate_archive(path, {"archive_sha256": "0" * 64})

    def test_existing_import_reused_only_if_every_byte_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_bytes(b"fixture")
            payloads = {"a.txt": b"fixture"}
            importer.exact_existing(root, payloads)
            (root / "a.txt").write_bytes(b"different")
            with self.assertRaisesRegex(ValueError, "bytes differ"):
                importer.exact_existing(root, payloads)
            self.assertEqual((root / "a.txt").read_bytes(), b"different")

    def test_extra_existing_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "extra").write_bytes(b"fixture")
            with self.assertRaisesRegex(ValueError, "inventory differs"):
                importer.exact_existing(root, {})


if __name__ == "__main__":
    unittest.main()
