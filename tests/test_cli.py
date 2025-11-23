"""Tests for CLI functionality."""

from typer.testing import CliRunner

from agent_smith.cli import app

runner = CliRunner()


def test_cli_app_exists():
    """Test that CLI app is properly initialized."""
    assert app is not None
    assert app.info.name == "smith"


def test_version_command():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Agent Smith" in result.stdout
    assert "v" in result.stdout


def test_config_show():
    """Test config show command."""
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Default Provider" in result.stdout or "Configuration" in result.stdout


def test_config_path():
    """Test config path command."""
    result = runner.invoke(app, ["config", "path"])
    assert result.exit_code == 0
    assert "agent-smith" in result.stdout


def test_config_get_existing_key():
    """Test getting an existing config key."""
    result = runner.invoke(app, ["config", "get", "default_provider"])
    assert result.exit_code == 0
    # Should show the provider name
    assert len(result.stdout) > 0


def test_config_get_nonexistent_key():
    """Test getting a non-existent config key."""
    result = runner.invoke(app, ["config", "get", "nonexistent_key_xyz"])
    assert result.exit_code == 0
    # Should either show None or error message


def test_config_set_requires_value():
    """Test that config set requires both key and value."""
    result = runner.invoke(app, ["config", "set", "test_key"])
    # Should error or ask for value
    assert "value" in result.stdout.lower() or result.exit_code == 1


def test_help_flag():
    """Test --help flag."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Agent Smith" in result.stdout
    assert "help" in result.stdout.lower()


def test_version_flag():
    """Test --version through version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0


def test_config_invalid_action():
    """Test config with invalid action."""
    result = runner.invoke(app, ["config", "invalid_action"])
    assert result.exit_code == 1
    assert "Unknown action" in result.stdout


def test_cli_with_verbose():
    """Test CLI with verbose flag."""
    # Testing that verbose flag is accepted
    result = runner.invoke(app, ["--verbose", "version"])
    # Should work with or without verbose output
    assert "Agent Smith" in result.stdout


def test_cli_with_debug():
    """Test CLI with debug flag."""
    result = runner.invoke(app, ["--debug", "version"])
    # Should work with debug flag
    assert "Agent Smith" in result.stdout


def test_cli_with_model_override():
    """Test CLI with model override."""
    result = runner.invoke(app, ["--model", "test-model", "version"])
    # Should accept model override
    assert "Agent Smith" in result.stdout
