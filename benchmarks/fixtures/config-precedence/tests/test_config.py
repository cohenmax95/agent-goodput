import unittest

from router.config import effective_config


class ConfigTests(unittest.TestCase):
    def test_later_layers_override_only_named_fields(self) -> None:
        self.assertEqual(
            {
                "model": "gpt-5.6-sol",
                "effort": "medium",
                "hooks": True,
            },
            effective_config(),
        )


if __name__ == "__main__":
    unittest.main()
