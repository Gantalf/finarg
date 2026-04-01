"""Load secrets from .env file."""

from dotenv import load_dotenv

from finarg.constants import ENV_FILE


def load_secrets() -> None:
    """Load ~/.finarg/.env into environment variables."""
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=True)
