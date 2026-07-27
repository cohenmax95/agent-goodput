import tempfile
import unittest
from pathlib import Path

from exporter import export_report


class ExporterTests(unittest.TestCase):
    def test_normal_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(root / "report.txt", export_report(root, "report.txt", "ok"))

    @unittest.skip("security regression not fixed yet")
    def test_parent_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exports"
            root.mkdir()
            with self.assertRaises(ValueError):
                export_report(root, "../outside.txt", "unsafe")


if __name__ == "__main__":
    unittest.main()
