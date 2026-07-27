import unittest

from phone import normalize_phone


class NormalizePhoneTests(unittest.TestCase):
    def test_ten_digit_number(self) -> None:
        self.assertEqual("+12395550100", normalize_phone("(239) 555-0100"))

    def test_existing_country_code(self) -> None:
        self.assertEqual("+12395550100", normalize_phone("1-239-555-0100"))

    def test_short_number_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_phone("555-0100")

    def test_non_us_number_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_phone("+44 20 7946 0958")


if __name__ == "__main__":
    unittest.main()
