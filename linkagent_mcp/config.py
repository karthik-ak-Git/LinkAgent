"""
Configuration management for LinkAgent MCP.

All settings are loaded from environment variables with sensible defaults.
Create a .env file in the project root or set env vars directly.

Environment Variables:
    LINKAGENT_CDP_PORT      — Chrome DevTools Protocol port (default: 9222)
    LINKAGENT_CDP_HOST      — CDP host address (default: 127.0.0.1)
    LINKAGENT_LOG_LEVEL     — Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    LINKAGENT_LOG_FILE      — Optional log file path (default: None, logs to stderr)
    LINKAGENT_SCREENSHOT_DIR — Directory for screenshots (default: ./screenshots)
    LINKAGENT_SERVER_NAME   — MCP server name reported to clients (default: linkagent)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    # CDP connection
    cdp_host: str = field(default_factory=lambda: os.getenv("LINKAGENT_CDP_HOST", "127.0.0.1"))
    cdp_port: int = field(default_factory=lambda: int(os.getenv("LINKAGENT_CDP_PORT", "9222")))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LINKAGENT_LOG_LEVEL", "INFO"))
    log_file: str | None = field(default_factory=lambda: os.getenv("LINKAGENT_LOG_FILE"))

    # Output
    screenshot_dir: Path = field(
        default_factory=lambda: Path(os.getenv("LINKAGENT_SCREENSHOT_DIR", "./screenshots"))
    )

    # MCP
    server_name: str = field(default_factory=lambda: os.getenv("LINKAGENT_SERVER_NAME", "linkagent"))

    @property
    def cdp_base_url(self) -> str:
        """Full CDP base URL (e.g. http://127.0.0.1:9222)."""
        return f"http://{self.cdp_host}:{self.cdp_port}"

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)


def get_config() -> Config:
    """Get the application configuration singleton."""
    return Config()
