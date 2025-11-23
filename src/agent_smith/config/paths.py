"""Cross-platform path management following XDG Base Directory spec."""

from pathlib import Path
from typing import Final

from platformdirs import user_cache_dir, user_config_dir, user_data_dir, user_log_dir

APP_NAME: Final[str] = "agent-smith"
APP_AUTHOR: Final[str] = "agent-smith"  # Used on Windows


class AppPaths:
    """Application directory paths (XDG-compliant)."""

    # Configuration directory
    CONFIG_DIR: Final[Path] = Path(user_config_dir(APP_NAME, APP_AUTHOR))

    # Data directory (conversations, persistent data)
    DATA_DIR: Final[Path] = Path(user_data_dir(APP_NAME, APP_AUTHOR))

    # Cache directory (temporary, can be deleted)
    CACHE_DIR: Final[Path] = Path(user_cache_dir(APP_NAME, APP_AUTHOR))

    # Log directory
    LOG_DIR: Final[Path] = Path(user_log_dir(APP_NAME, APP_AUTHOR))

    # Specific file paths
    SETTINGS_FILE: Final[Path] = CONFIG_DIR / "settings.toml"
    SECRETS_FILE: Final[Path] = CONFIG_DIR / ".secrets.toml"
    PROVIDERS_FILE: Final[Path] = CONFIG_DIR / "providers.toml"
    PERMISSIONS_FILE: Final[Path] = CONFIG_DIR / "permissions.toml"

    # Data paths
    CONVERSATIONS_DIR: Final[Path] = DATA_DIR / "conversations"
    CACHE_DB: Final[Path] = CACHE_DIR / "file_contents.db"

    # Log file
    LOG_FILE: Final[Path] = LOG_DIR / "agent-smith.log"

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all required directories if they don't exist."""
        for dir_path in [
            cls.CONFIG_DIR,
            cls.DATA_DIR,
            cls.CACHE_DIR,
            cls.LOG_DIR,
            cls.CONVERSATIONS_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_conversation_path(cls, conversation_id: str) -> Path:
        """Get path for a specific conversation log."""
        return cls.CONVERSATIONS_DIR / f"{conversation_id}.json"


# Initialize directories on import
AppPaths.ensure_directories()
