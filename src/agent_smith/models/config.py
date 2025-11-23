"""Configuration models."""

from pydantic import BaseModel


class ModelConfig(BaseModel):
    """Configuration for a specific model."""

    name: str
    max_tokens: int = 8192
    temperature: float = 1.0
    top_p: float | None = None
    top_k: int | None = None


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    name: str
    base_url: str
    api_version: str | None = None
    timeout: float = 600.0
    max_retries: int = 3
    default_model: str = ""
    max_tokens: int = 8192
    temperature: float = 1.0


class APIUsage(BaseModel):
    """API usage statistics."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        return self.input_tokens + self.output_tokens

    def add(self, other: "APIUsage") -> "APIUsage":
        """Add usage from another APIUsage object."""
        return APIUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens
            + other.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens
            + other.cache_read_input_tokens,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "APIUsage":
        """Create from dictionary (API response)."""
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cache_creation_input_tokens=data.get("cache_creation_input_tokens", 0),
            cache_read_input_tokens=data.get("cache_read_input_tokens", 0),
        )
