import unittest

from mailops.state import Disposition, register_scanned_response


class MailboxStateTests(unittest.TestCase):
    def test_scan_history_image_is_held_after_matching(self) -> None:
        result = register_scanned_response(
            source="scan_history",
            image_only=True,
            matched=True,
        )
        self.assertEqual(Disposition.HELD_FOR_SCAN, result)


if __name__ == "__main__":
    unittest.main()
