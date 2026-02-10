"""Tests for config module functionality."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        from pulse.config import Config

        self.config = Config(config_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test Config initialization."""
        self.assertEqual(self.config.config_dir, Path(self.temp_dir))
        self.assertTrue(self.config.config_file.name.endswith("settings.json"))

    def test_default_values(self):
        """Test that default values are set correctly."""
        self.assertEqual(self.config.idle_threshold, 300)
        self.assertFalse(self.config.fast_mode)
        self.assertTrue(self.config.verbose_logging)
        self.assertEqual(self.config.sync_endpoint, "")

    def test_get_returns_default_for_missing_key(self):
        """Test get returns default for missing key."""
        result = self.config.get("nonexistent_key", "default_value")
        self.assertEqual(result, "default_value")

    def test_set_updates_value(self):
        """Test set updates configuration value."""
        self.config.set("idle_threshold", 600)
        self.assertEqual(self.config.idle_threshold, 600)

    def test_update_multiple_values(self):
        """Test updating multiple values at once."""
        self.config.update(
            {
                "idle_threshold": 600,
                "fast_mode": True,
            }
        )
        self.assertEqual(self.config.idle_threshold, 600)
        self.assertTrue(self.config.fast_mode)

    def test_reset_to_defaults(self):
        """Test resetting to default values."""
        self.config.set("idle_threshold", 600)
        self.config.reset_to_defaults()
        self.assertEqual(self.config.idle_threshold, 300)

    def test_get_all_returns_copy(self):
        """Test that get_all returns a copy of config."""
        config_copy = self.config.get_all()
        config_copy["idle_threshold"] = 999

        # Original should be unchanged
        self.assertEqual(self.config.idle_threshold, 300)

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        self.config.set("idle_threshold", 600)
        self.config.save()

        # Create a new config instance
        from pulse.config import Config

        new_config = Config(config_dir=self.temp_dir)

        self.assertEqual(new_config.idle_threshold, 600)

    def test_property_accessors(self):
        """Test property accessors for common settings."""
        # Test setters
        self.config.idle_threshold = 600
        self.config.fast_mode = True
        self.config.verbose_logging = False
        self.config.sync_endpoint = "https://example.com"

        # Test getters
        self.assertEqual(self.config.idle_threshold, 600)
        self.assertTrue(self.config.fast_mode)
        self.assertFalse(self.config.verbose_logging)
        self.assertEqual(self.config.sync_endpoint, "https://example.com")


class TestConfigFileHandling(unittest.TestCase):
    """Test cases for config file handling edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_handles_corrupt_config_file(self):
        """Test handling of corrupt config file."""
        # Create a corrupt config file
        config_dir = Path(self.temp_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "settings.json"
        with open(config_file, "w") as f:
            f.write("not valid json {{{")

        from pulse.config import Config

        config = Config(config_dir=self.temp_dir)

        # Should use default values
        self.assertEqual(config.idle_threshold, 300)

    def test_handles_missing_keys_in_file(self):
        """Test merging config file with missing keys."""
        # Create a partial config file
        config_dir = Path(self.temp_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "settings.json"
        with open(config_file, "w") as f:
            json.dump({"idle_threshold": 600}, f)

        from pulse.config import Config

        config = Config(config_dir=self.temp_dir)

        # Custom value should be used
        self.assertEqual(config.idle_threshold, 600)
        # Default values should be present
        self.assertFalse(config.fast_mode)


class TestDataDirProperty(unittest.TestCase):
    """Test cases for the data_dir property."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        from pulse.config import Config

        self.config = Config(config_dir=self.temp_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_default_data_dir_on_macos(self):
        """Test that default data_dir points to Application Support on macOS."""
        with patch("sys.platform", "darwin"):
            result = self.config.data_dir
        self.assertIn("Application Support", str(result))
        self.assertIn("Pulse", str(result))
        self.assertTrue(str(result).endswith("data"))

    def test_custom_data_dir(self):
        """Test that a custom data_dir is returned when set."""
        self.config.data_dir = "/tmp/custom_pulse_data"
        self.assertEqual(self.config.data_dir, Path("/tmp/custom_pulse_data"))

    def test_empty_data_dir_uses_default(self):
        """Test that empty string falls back to platform default."""
        self.config.set("data_dir", "")
        with patch("sys.platform", "darwin"):
            result = self.config.data_dir
        self.assertIn("Application Support", str(result))


class TestConfigFirstLaunch(unittest.TestCase):
    """Test cases for first-launch config file creation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_creates_settings_file_on_first_launch(self):
        """Test that settings.json is written on first launch."""
        from pulse.config import Config

        Config(config_dir=self.temp_dir)
        settings_file = Path(self.temp_dir) / "settings.json"
        self.assertTrue(settings_file.exists())
        with open(settings_file) as f:
            data = json.load(f)
        self.assertIn("data_dir", data)
        self.assertIn("idle_threshold", data)

    def test_backfills_new_keys(self):
        """Test that new default keys are written back to existing config."""
        config_file = Path(self.temp_dir) / "settings.json"
        # Write a config that is missing the data_dir key
        with open(config_file, "w") as f:
            json.dump({"idle_threshold": 600}, f)

        from pulse.config import Config

        config = Config(config_dir=self.temp_dir)
        self.assertEqual(config.idle_threshold, 600)

        # File should now contain all default keys
        with open(config_file) as f:
            data = json.load(f)
        self.assertIn("data_dir", data)
        self.assertIn("idle_threshold", data)
        self.assertEqual(data["idle_threshold"], 600)


class TestLoadConfigFromEnv(unittest.TestCase):
    """Test cases for loading config from environment variables."""

    def test_loads_string_values(self):
        """Test loading string values from environment."""
        with patch.dict(os.environ, {"PULSE_ENDPOINT": "https://test.com"}):
            from pulse.config import load_config_from_env

            env_config = load_config_from_env()

        self.assertEqual(env_config.get("sync_endpoint"), "https://test.com")

    def test_loads_integer_values(self):
        """Test loading integer values from environment."""
        with patch.dict(os.environ, {"PULSE_IDLE_THRESHOLD": "600"}):
            from pulse.config import load_config_from_env

            env_config = load_config_from_env()

        self.assertEqual(env_config.get("idle_threshold"), 600)

    def test_loads_boolean_values(self):
        """Test loading boolean values from environment."""
        with patch.dict(os.environ, {"PULSE_FAST_MODE": "true"}):
            from pulse.config import load_config_from_env

            env_config = load_config_from_env()

        self.assertTrue(env_config.get("fast_mode"))

    def test_handles_invalid_integer(self):
        """Test handling of invalid integer values."""
        with patch.dict(os.environ, {"PULSE_IDLE_THRESHOLD": "not_a_number"}):
            with patch("builtins.print"):
                from pulse.config import load_config_from_env

                env_config = load_config_from_env()

        # Should not set invalid value
        self.assertNotIn("idle_threshold", env_config)


class TestGetConfig(unittest.TestCase):
    """Test cases for get_config singleton."""

    def test_returns_config_instance(self):
        """Test that get_config returns a Config instance."""
        from pulse.config import get_config

        config = get_config()

        from pulse.config import Config

        self.assertIsInstance(config, Config)

    def test_returns_same_instance(self):
        """Test that get_config returns the same instance."""
        from pulse.config import get_config, reload_config

        # Reset global state
        reload_config()

        config1 = get_config()
        config2 = get_config()

        self.assertIs(config1, config2)


if __name__ == "__main__":
    unittest.main()
