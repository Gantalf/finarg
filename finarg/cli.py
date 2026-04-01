"""CLI entry points: finarg, finarg init, finarg chat."""

from __future__ import annotations

import asyncio
import os
import sys

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from finarg.constants import CONFIG_FILE, ENV_FILE, FINARG_HOME, SKILLS_DIR

console = Console()


def main() -> None:
    """Main entry point."""
    args = sys.argv[1:]

    if not args:
        _run_tui()
    elif args[0] == "init":
        _run_init()
    elif args[0] == "chat":
        asyncio.run(_run_chat())
    elif args[0] == "version":
        from finarg import __version__

        console.print(f"Finarg v{__version__}")
    else:
        console.print(f"[red]Unknown command:[/] {args[0]}")
        console.print("Usage: finarg [init|chat|version]")
        sys.exit(1)


def _run_init() -> None:
    """Interactive setup wizard."""
    console.print()
    console.print(
        Panel(
            "[bold #00ff88]Welcome to Finarg v0.1.0[/]\n"
            "[#8892b0]Let's set up your AI financial agent[/]",
            border_style="#e94560",
            padding=(1, 4),
        )
    )
    console.print()

    # Ensure directories exist
    FINARG_HOME.mkdir(parents=True, exist_ok=True)
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    env_lines: list[str] = []

    # Step 1: LLM Provider
    console.print("[bold #4fc3f7]1/2 LLM Provider[/]")
    provider = Prompt.ask(
        "  Provider",
        choices=["anthropic", "openai", "moonshot"],
        default="anthropic",
    )

    key_name = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
    }[provider]

    api_key = Prompt.ask(f"  {key_name}")
    if api_key:
        env_lines.append(f"{key_name}={api_key}")
        console.print(f"  [#00ff88]\u2713 {provider} key saved[/]")
    else:
        console.print("  [#ff4444]\u2717 No key provided. Agent will not work without an LLM key.[/]")

    console.print()

    # Step 2: Ripio Trade
    console.print("[bold #4fc3f7]2/2 Ripio Trade (optional)[/]")
    console.print("  [#8892b0]Enables wallet management and crypto transfers.[/]")
    console.print("  [#8892b0]Get your keys at: https://trade.ripio.com/market/api/token[/]")

    has_ripio = Confirm.ask("  Do you have Ripio Trade API keys?", default=False)
    if has_ripio:
        ripio_key = Prompt.ask("  RIPIO_TRADE_API_KEY")
        ripio_secret = Prompt.ask("  RIPIO_TRADE_API_SECRET")
        if ripio_key and ripio_secret:
            env_lines.append(f"RIPIO_TRADE_API_KEY={ripio_key}")
            env_lines.append(f"RIPIO_TRADE_API_SECRET={ripio_secret}")
            console.print("  [#00ff88]\u2713 Ripio keys saved[/]")
        else:
            console.print("  [#ffa726]Skipped. You can add keys later in ~/.finarg/.env[/]")
    else:
        console.print("  [#8892b0]Skipped. BCRA rates and chat still work without Ripio.[/]")

    # Write .env
    ENV_FILE.write_text("\n".join(env_lines) + "\n")
    ENV_FILE.chmod(0o600)

    # Write config.yaml
    config = {
        "model": {
            "default": {
                "anthropic": "claude-sonnet-4-20250514",
                "openai": "gpt-4o",
                "moonshot": "kimi-k2-thinking",
            }[provider],
            "provider": provider,
        },
        "agent": {"max_turns": 30},
        "apis": {
            "ripio_trade": {"enabled": has_ripio},
            "bcra": {"enabled": True},
        },
        "tui": {
            "theme": "dark",
            "ticker_pairs": ["BTC_USDT", "ETH_USDT", "USDT_ARS"],
            "refresh_interval": 30,
        },
    }
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print()
    console.print(
        Panel(
            f"[#00ff88]\u2713 Config saved to[/] {CONFIG_FILE}\n"
            f"[#00ff88]\u2713 Secrets saved to[/] {ENV_FILE}\n\n"
            "[bold]Run [#4fc3f7]finarg[/] to launch![/]",
            border_style="#00ff88",
            padding=(1, 4),
        )
    )


def _run_tui() -> None:
    """Launch the full TUI application."""
    from finarg.app import FinargApp
    from finarg.config import load_config

    config = load_config()
    agent = _build_agent(config)

    app = FinargApp(agent=agent)
    app.run()


async def _run_chat() -> None:
    """Simple chat mode without TUI (for debugging / piping)."""
    from finarg.config import load_config

    config = load_config()
    agent = _build_agent(config)

    if not agent:
        console.print("[red]No LLM API key configured. Run `finarg init` first.[/]")
        return

    console.print("[bold #00ff88]Finarg Chat Mode[/] (type 'exit' to quit)\n")

    while True:
        try:
            user_input = Prompt.ask("[bold #4fc3f7]\u25b6 You[/]")
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.lower() in ("exit", "quit", "q"):
            break

        try:
            response = await agent.run_conversation(user_input)
            console.print(f"\n[bold #00ff88]\u25c0 Finarg:[/] {response}\n")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/]\n")


def _build_agent(config):
    """Build the agent from config. Returns None if no API key."""
    from finarg.config.loader import FinargConfig

    api_key = config.get_llm_api_key()
    if not api_key:
        return None

    # Import here to avoid circular imports
    from finarg.agent.loop import FinargAgent
    from finarg.agent.session import SessionStore
    from finarg.constants import DB_FILE, SKILLS_DIR
    from finarg.tools.registry import registry

    # Load built-in tools
    from finarg.tools.wallet import register_wallet_tools
    from finarg.tools.transfer import register_transfer_tools
    from finarg.tools.market_data import register_market_data_tools

    from finarg.tools.web import register_web_tools

    register_wallet_tools()
    register_transfer_tools()
    register_market_data_tools()
    register_web_tools()

    from finarg.tools.browser import register_browser_tools
    register_browser_tools()

    # skill_creator registers itself on import
    import finarg.tools.skill_creator  # noqa: F401

    # Load user skills
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    registry.load_skills_dir(SKILLS_DIR)

    # Build the right provider based on config
    llm_provider = _build_provider(config.model.provider, api_key, config.model.default)

    session_store = SessionStore(DB_FILE)

    return FinargAgent(
        config=config,
        provider=llm_provider,
        registry=registry,
        session_store=session_store,
    )


def _build_provider(provider_name: str, api_key: str, model: str):
    """Build the LLM provider based on config."""
    if provider_name == "anthropic":
        from finarg.agent.providers.anthropic import AnthropicProvider
        return AnthropicProvider(api_key=api_key, model=model)

    elif provider_name == "openai":
        from finarg.agent.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model)

    elif provider_name == "moonshot":
        from finarg.agent.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url="https://api.moonshot.ai/v1",
        )

    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use anthropic, openai, or moonshot.")
