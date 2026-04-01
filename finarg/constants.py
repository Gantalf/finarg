"""Paths and defaults for Finarg."""

from pathlib import Path

FINARG_HOME = Path.home() / ".finarg"
CONFIG_FILE = FINARG_HOME / "config.yaml"
ENV_FILE = FINARG_HOME / ".env"
SKILLS_DIR = FINARG_HOME / "skills"
DB_FILE = FINARG_HOME / "finarg.db"
SOUL_FILE = Path(__file__).parent / "SOUL.md"

DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_PROVIDER = "anthropic"
MAX_AGENT_TURNS = 30
RIPIO_TRADE_BASE_URL = "https://api.ripiotrade.co/v4"
BCRA_BASE_URL = "https://api.bcra.gob.ar"
