"""Application settings using dynaconf."""

from dynaconf import Dynaconf, Validator

from .paths import AppPaths


def _create_default_configs() -> None:
    """Create default configuration files if they don't exist."""

    # Default settings.toml
    if not AppPaths.SETTINGS_FILE.exists():
        default_settings = """# Agent Smith Configuration
# https://github.com/brandonrc/agent-smith

[default]
# Default LLM provider (anthropic, openai, bedrock, vertex)
default_provider = "anthropic"

# Default models
large_model = "claude-sonnet-4-5-20250929"
small_model = "claude-3-5-haiku-20241022"

# UI Settings
show_cost = true
enable_prompt_caching = true
max_parallel_tools = 10

# Permission settings
skip_permissions = false
auto_approve_safe_tools = ["Read", "Glob", "Grep"]

# Logging
verbose = false
debug = false
log_level = "INFO"

# Feature flags
enable_architect_tool = false
enable_binary_feedback = false
enable_extended_thinking = true

[development]
# Development environment overrides
verbose = true
debug = true
log_level = "DEBUG"
"""
        AppPaths.SETTINGS_FILE.write_text(default_settings)

    # Default providers.toml
    if not AppPaths.PROVIDERS_FILE.exists():
        default_providers = """# LLM Provider Configuration

[anthropic]
base_url = "https://api.anthropic.com"
api_version = "2023-06-01"
max_tokens = 8192
temperature = 1.0
timeout = 600.0

[openai]
base_url = "https://api.openai.com/v1"
max_tokens = 8192
temperature = 1.0
timeout = 600.0

[bedrock]
region = "us-west-2"
max_tokens = 8192

[vertex]
project_id = ""
region = "us-central1"
max_tokens = 8192
"""
        AppPaths.PROVIDERS_FILE.write_text(default_providers)

    # Default .secrets.toml (gitignored)
    if not AppPaths.SECRETS_FILE.exists():
        default_secrets = """# API Keys and Secrets
# DO NOT COMMIT THIS FILE!

[default]
# Anthropic API Key
anthropic_api_key = ""

# OpenAI API Key
openai_api_key = ""

# Optional: Use system keyring instead
# Set to true to store keys in OS credential manager
use_keyring = false
"""
        AppPaths.SECRETS_FILE.write_text(default_secrets)
        AppPaths.SECRETS_FILE.chmod(0o600)  # Secure permissions


# Create default configs
_create_default_configs()

# Dynaconf settings object
settings = Dynaconf(
    # Where to find config files
    settings_files=[
        str(AppPaths.SETTINGS_FILE),
        str(AppPaths.PROVIDERS_FILE),
        str(AppPaths.SECRETS_FILE),
    ],
    # Environment variables prefix (SMITH_*)
    envvar_prefix="SMITH",
    # Support .env files in current directory
    load_dotenv=True,
    # Environments (development, production, testing)
    environments=True,
    env="default",
    # Merge all sources (env vars override files)
    merge_enabled=True,
    # Validators (ensure required fields exist)
    validators=[
        # Provider settings
        Validator(
            "default_provider",
            must_exist=True,
            is_in=["anthropic", "openai", "bedrock", "vertex"],
        ),
        # Model settings
        Validator("large_model", must_exist=True),
        Validator("small_model", must_exist=True),
        # Tool settings
        Validator("max_parallel_tools", gte=1, lte=20),
        # Logging
        Validator(
            "log_level",
            is_in=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        ),
    ],
)

# Validate on load
settings.validators.validate()


def get_api_key(provider: str) -> str | None:
    """
    Get API key for a provider.

    Priority:
    1. Environment variable (SMITH_ANTHROPIC_API_KEY)
    2. Keyring (if use_keyring=true)
    3. .secrets.toml file

    Args:
        provider: Provider name (anthropic, openai, etc.)

    Returns:
        API key if found, None otherwise
    """
    import keyring

    # Check settings (env vars override files)
    key_name = f"{provider}_api_key"
    api_key = settings.get(key_name)

    if api_key:
        return api_key

    # Try keyring if enabled
    if settings.get("use_keyring", False):
        try:
            return keyring.get_password("agent-smith", f"{provider}_api_key")
        except Exception:
            pass

    return None


def set_api_key(provider: str, api_key: str, use_keyring: bool = False) -> None:
    """
    Store API key securely.

    Args:
        provider: Provider name (anthropic, openai, etc.)
        api_key: The API key to store
        use_keyring: If True, store in OS keyring instead of file
    """
    import keyring

    if use_keyring:
        keyring.set_password("agent-smith", f"{provider}_api_key", api_key)
        # Update setting to use keyring
        settings.set("use_keyring", True)
    else:
        # Write to .secrets.toml
        from dynaconf import loaders
        from dynaconf.utils.boxing import DynaBox

        secrets_data = loaders.toml_loader.load(str(AppPaths.SECRETS_FILE))
        secrets_data = DynaBox(secrets_data)

        if "default" not in secrets_data:
            secrets_data["default"] = {}

        secrets_data["default"][f"{provider}_api_key"] = api_key

        loaders.toml_loader.write(
            str(AppPaths.SECRETS_FILE),
            secrets_data.to_dict(),
            merge=True,
        )
        AppPaths.SECRETS_FILE.chmod(0o600)
