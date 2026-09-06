import unittest

from src.command_router import _bash_quote, _cmd_quote, _powershell_quote


class CommandRouterTests(unittest.TestCase):
    def test_bash_quote_handles_single_quote(self):
        self.assertEqual(_bash_quote("a'b"), "'a'\\''b'")

    def test_powershell_quote_doubles_single_quote(self):
        self.assertEqual(_powershell_quote("a'b"), "'a''b'")

    def test_cmd_quote_rejects_embedded_double_quote(self):
        with self.assertRaises(ValueError):
            _cmd_quote('a"b')


if __name__ == "__main__":
    unittest.main()
