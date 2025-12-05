"""Configuration management for ESG Analyzer."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class EdgarConfig(BaseModel):
    """SEC EDGAR API configuration."""

    user_agent: str = Field(
        default="ESGAnalyzer contact@example.com",
        description="User-Agent header required by SEC",
    )
    requests_per_second: int = Field(default=10, description="Rate limit")
    base_url: str = Field(default="https://data.sec.gov")
    search_url: str = Field(default="https://efts.sec.gov/LATEST/search-index")


class DownloadConfig(BaseModel):
    """Download settings."""

    concurrency: int = Field(default=5, description="Max concurrent downloads")
    max_retries: int = Field(default=3)
    timeout: int = Field(default=30, description="Timeout in seconds")
    cache_dir: str = Field(default="cache")


class AnalysisConfig(BaseModel):
    """Analysis settings."""

    context_window: int = Field(default=1, description="Sentences around match")
    max_matches_per_report: int = Field(default=50)
    min_keyword_length: int = Field(default=3)


class OutputConfig(BaseModel):
    """Output settings."""

    output_dir: str = Field(default="output")
    default_format: str = Field(default="console")
    include_context: bool = Field(default=True)
    highlight_keywords: bool = Field(default=True)


class Settings(BaseModel):
    """Application settings."""

    edgar: EdgarConfig = Field(default_factory=EdgarConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from YAML file or use defaults."""
    if config_path is None:
        # Look for config in standard locations
        possible_paths = [
            Path("config/settings.yaml"),
            Path("settings.yaml"),
            Path.home() / ".config" / "esg-analyzer" / "settings.yaml",
        ]
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

    if config_path and config_path.exists():
        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return Settings(**data)

    return Settings()


def load_keywords(keywords_path: Path | None = None) -> dict[str, dict[str, list[str]]]:
    """Load keyword taxonomy from YAML file.

    Returns:
        Nested dict: category -> subcategory -> list of keywords
        Example: {"environmental": {"climate": ["carbon neutrality", "net zero"]}}
    """
    if keywords_path is None:
        possible_paths = [
            Path("config/keywords.yaml"),
            Path("keywords.yaml"),
        ]
        for path in possible_paths:
            if path.exists():
                keywords_path = path
                break

    if keywords_path is None or not keywords_path.exists():
        raise FileNotFoundError("Keywords file not found. Please provide config/keywords.yaml")

    with open(keywords_path) as f:
        data: dict[str, dict[str, list[str]]] = yaml.safe_load(f) or {}

    return data


# Global settings instance (lazy-loaded)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
