"""Tests for utils module functionality."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestGetDataDirectory(unittest.TestCase):
    """Test cases for get_data_directory function."""

    def _make_config(self, data_dir=""):
        """Create a mock config with the given data_dir."""
        from unittest.mock import MagicMock

        cfg = MagicMock()
        cfg.get.return_value = data_dir
        if data_dir:
            cfg.data_dir = Path(data_dir)
        else:
            cfg.data_dir = (
                Path.home() / "Library" / "Application Support" / "Pulse" / "data"
            )
        return cfg

    def test_returns_path_object(self):
        """Test that function returns a Path object."""
        from pulse.utils import get_data_directory

        with patch("pulse.config.get_config", return_value=self._make_config()):
            result = get_data_directory()
        self.assertIsInstance(result, Path)

    def test_returns_default_macos_path(self):
        """Test default macOS path when no custom data_dir is configured."""
        from pulse.utils import get_data_directory

        with patch("pulse.config.get_config", return_value=self._make_config()):
            result = get_data_directory()
        self.assertIn("Library", str(result))
        self.assertIn("Application Support", str(result))
        self.assertIn("Pulse", str(result))

    def test_returns_custom_path_from_config(self):
        """Test that a custom data_dir from settings is respected."""
        from pulse.utils import get_data_directory

        custom = tempfile.mkdtemp()
        try:
            with patch(
                "pulse.config.get_config",
                return_value=self._make_config(custom),
            ):
                result = get_data_directory()
            self.assertEqual(result, Path(custom))
            self.assertTrue(result.exists())
        finally:
            import shutil

            shutil.rmtree(custom)

    def test_directory_exists_after_call(self):
        """Test that directory is created if it doesn't exist."""
        from pulse.utils import get_data_directory

        custom = tempfile.mkdtemp()
        import shutil

        shutil.rmtree(custom)  # Remove so get_data_directory re-creates it
        try:
            with patch(
                "pulse.config.get_config",
                return_value=self._make_config(custom),
            ):
                result = get_data_directory()
            self.assertTrue(result.exists())
        finally:
            if Path(custom).exists():
                shutil.rmtree(custom)


class TestViewActivityFile(unittest.TestCase):
    """Test cases for view_activity_file function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_view_valid_activity_file(self):
        """Test viewing a valid activity file."""
        # Create a test file
        filepath = Path(self.temp_dir) / "activity_20240115_1430.json"
        test_data = {"App1": 30.5, "App2": 25.0}
        with open(filepath, "w") as f:
            json.dump(test_data, f)

        from pulse.utils import view_activity_file

        # Should not raise any exceptions
        with patch("builtins.print"):
            view_activity_file(str(filepath))

    def test_view_file_with_unicode(self):
        """Test viewing file with Unicode characters."""
        filepath = Path(self.temp_dir) / "activity_20240115_1430.json"
        test_data = {"App — Test": 30.5, "App • Demo": 25.0}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False)

        from pulse.utils import view_activity_file

        with patch("builtins.print"):
            view_activity_file(str(filepath))

    def test_view_invalid_json_file(self):
        """Test viewing invalid JSON file."""
        filepath = Path(self.temp_dir) / "activity_20240115_1430.json"
        with open(filepath, "w") as f:
            f.write("not valid json")

        from pulse.utils import view_activity_file

        with patch("builtins.print") as mock_print:
            view_activity_file(str(filepath))
            # Should print error message
            calls = [str(call) for call in mock_print.call_args_list]
            error_printed = any("[ERROR]" in str(call) for call in calls)
            self.assertTrue(error_printed)

    def test_view_nonexistent_file(self):
        """Test viewing non-existent file."""
        filepath = Path(self.temp_dir) / "nonexistent.json"

        from pulse.utils import view_activity_file

        with patch("builtins.print"):
            # Should handle gracefully
            view_activity_file(str(filepath))


class TestViewActivityFileParsing(unittest.TestCase):
    """Test cases for filename parsing in view_activity_file."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_parses_standard_filename(self):
        """Test parsing standard activity filename."""
        filepath = Path(self.temp_dir) / "activity_20240115_1430.json"
        with open(filepath, "w") as f:
            json.dump({"App1": 30.0}, f)

        from pulse.utils import view_activity_file

        with patch("builtins.print") as mock_print:
            view_activity_file(str(filepath))
            # Should print date in formatted form
            calls = str(mock_print.call_args_list)
            self.assertIn("2024-01-15", calls)

    def test_handles_non_standard_filename(self):
        """Test handling non-standard filename."""
        filepath = Path(self.temp_dir) / "custom_file.json"
        with open(filepath, "w") as f:
            json.dump({"App1": 30.0}, f)

        from pulse.utils import view_activity_file

        with patch("builtins.print"):
            # Should not raise exception
            view_activity_file(str(filepath))


class TestUtilsMain(unittest.TestCase):
    """Test cases for utils main function."""

    def test_main_shows_usage_with_no_args(self):
        """Test main shows usage when no arguments provided."""
        from pulse.utils import main

        with patch("sys.argv", ["utils.py"]):
            with patch("builtins.print") as mock_print:
                main()
                calls = str(mock_print.call_args_list)
                self.assertIn("Usage", calls)

    def test_main_handles_nonexistent_file(self):
        """Test main handles nonexistent file gracefully."""
        from pulse.utils import main

        with patch("sys.argv", ["utils.py", "/nonexistent/file.json"]):
            with patch("builtins.print") as mock_print:
                main()
                calls = str(mock_print.call_args_list)
                self.assertIn("[ERROR]", calls)


if __name__ == "__main__":
    unittest.main()
