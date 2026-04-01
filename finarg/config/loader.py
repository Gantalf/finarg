"""YAML config loading with Pydantic validation."""

from __future__ import annotations

import os
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from finarg.config.secrets import load_secrets
from finarg.constants import CONFIG_FILE, DEFAULT_MODEL, DEFAULT_PROVIDER, MAX_AGENT_TURNS


class ModelConfig(BaseModel):
    default: str = DEFAULT_MODEL
    provider: str = DEFAULT_PROVIDER


class AgentConfig(BaseModel):
    max_turns: int = MAX_AGENT_TURNS


class APIConfig(BaseModel):
    enabled: bool = True
    rate_limit: float = 1.0


class APIsConfig(BaseModel):
    ripio_trade: APIConfig = Field(default_factory=APIConfig)
    bcra: APIConfig = Field(default_factory=APIConfig)


class TUIConfig(BaseModel):
    theme: str = "dark"
    ticker_pairs: list[str] = Field(default_factory=lambda: ["BTC_USDT", "ETH_USDT", "USDT_ARS"])
    refresh_interval: int = 30


class FinargConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    apis: APIsConfig = Field(default_factory=APIsConfig)
    tui: TUIConfig = Field(default_factory=TUIConfig)

    # Resolved from environment after loading
    anthropic_api_key: Optional[str] = None
    ripio_trade_api_key: Optional[str] = None
    ripio_trade_api_secret: Optional[str] = None

    def has_ripio(self) -> bool:
        return bool(self.ripio_trade_api_key and self.ripio_trade_api_secret)


def load_config() -> FinargConfig:
    """Load config from YAML file + environment variables."""
    load_secrets()

    data = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}

    config = FinargConfig(**data)

    # Resolve secrets from environment
    config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    config.ripio_trade_api_key = os.getenv("RIPIO_TRADE_API_KEY")
    config.ripio_trade_api_secret = os.getenv("RIPIO_TRADE_API_SECRET")

    return config
