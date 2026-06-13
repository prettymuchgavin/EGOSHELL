import sys
import unittest
from unittest.mock import patch
import main


class TestUninstall(unittest.TestCase):
    @patch("main.sys")
    @patch("egoshell.uninstall.run_uninstall")
    def test_uninstall_subcommand(self, mock_run_uninstall, mock_sys):
        mock_sys.argv = ["main.py", "uninstall"]
        main.main()
        mock_run_uninstall.assert_called_once()


if __name__ == "__main__":
    unittest.main()
