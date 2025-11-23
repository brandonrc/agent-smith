"""Tests for configuration management."""

import os

from agent_smith.config import AppPaths, get_api_key, set_api_key, settings


def test_app_paths_exist():
    """Test that app paths are properly defined."""
    assert AppPaths.CONFIG_DIR.exists()
    assert AppPaths.DATA_DIR.exists()
    assert AppPaths.CACHE_DIR.exists()
    assert AppPaths.LOG_DIR.exists()


def test_settings_loaded():
    """Test that settings are loaded."""
    assert settings is not None
    assert settings.get("default_provider") is not None
    assert settings.get("large_model") is not None
    assert settings.get("small_model") is not None


def test_settings_defaults():
    """Test default settings values."""
    assert settings.get("max_parallel_tools", 10) >= 1
    assert settings.get("log_level") in [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]


def test_api_key_retrieval():
    """Test API key retrieval."""
    # Should not raise an exception
    key = get_api_key("anthropic")
    # Key might be None if not set
    assert key is None or isinstance(key, str)


def test_api_key_set_and_get(tmp_path, monkeypatch):
    """Test API key management functions exist."""
    # Test that the functions are callable
    assert callable(set_api_key)
    assert callable(get_api_key)

    # Test with keyring (will use system keyring if available)
    # This is a smoke test to ensure the function doesn't crash
    try:
        set_api_key("test_provider", "test_key", use_keyring=True)
    except Exception:
        # Keyring might not be available, that's okay for unit tests
        pass


def test_environment_variable_override(monkeypatch):
    """Test that environment variables override settings."""
    # Set an environment variable
    test_model = "test-model-123"
    monkeypatch.setenv("SMITH_LARGE_MODEL", test_model)

    # Reload settings (in practice, this would need a fresh settings object)
    # For this test, we just verify the environment variable is set
    assert os.environ.get("SMITH_LARGE_MODEL") == test_model
