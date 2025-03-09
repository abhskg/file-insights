"""
Configuration settings for file-insights.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple


@dataclass
class Config:
    """Configuration settings for the file-insights tool."""

    # Default patterns to exclude
    DEFAULT_EXCLUDE_PATTERNS = (
        "**/.*",  # Hidden files and directories
        "**/__pycache__/**",
        "**/*.pyc",
        "**/node_modules/**",
        "**/venv/**",
        "**/.git/**",
        "**/.svn/**",
        "**/.hg/**",
        "**/.vscode/**",
        "**/.idea/**",
    )

    # Default settings
    recursive: bool = True
    exclude_patterns: Tuple[str, ...] = DEFAULT_EXCLUDE_PATTERNS
    max_preview_size: int = 1000  # Characters
    hash_algorithm: str = "md5"

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """
        Load configuration from a file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Config object with settings from the file
        """
        # This is a placeholder for future implementation
        # For now, just return default config
        return cls()


# Global config instance
config = Config()
