"""Tests for the desktop launcher routing."""

import sys
import unittest
from unittest.mock import patch
import main


class TestDesktop(unittest.TestCase):
    @patch("main.sys")
    @patch("egoshell.ui.desktop.run_desktop")
    def test_desktop_subcommand(self, mock_run_desktop, mock_sys):
        mock_sys.argv = ["main.py", "desktop"]
        main.main()
        mock_run_desktop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
