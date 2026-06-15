"""Tests for the setup subcommand routing."""

import sys
import unittest
from unittest.mock import patch
import main


class TestSetupSubcommand(unittest.TestCase):
    @patch("main.sys")
    @patch("setup.main")
    def test_setup_subcommand(self, mock_setup_main, mock_sys):
        mock_sys.argv = ["main.py", "setup"]
        main.main()
        mock_setup_main.assert_called_once()


if __name__ == "__main__":
    unittest.main()
