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


def _install_bundled_skills() -> None:
    """Copy bundled skills to ~/.finarg/skills/ if not already present."""
    import shutil
    from pathlib import Path

    bundled_dir = Path(__file__).parent / "bundled_skills"
    if not bundled_dir.is_dir():
        return

    for skill_dir in bundled_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        target = SKILLS_DIR / skill_dir.name
        if not target.exists():
            shutil.copytree(skill_dir, target)
            console.print(f"  [#00ff88]\u2713[/] Installed bundled skill: {skill_dir.name}")


def main() -> None:
    """Main entry point."""
    args = sys.argv[1:]

    if not args or (args and args[0] == "chat"):
        asyncio.run(_run_chat())
    elif args[0] == "init":
        _run_init()
    elif args[0] == "version":
        from finarg import __version__

        console.print(f"Finarg v{__version__}")
    elif args[0] == "config":
        _run_config(args[1:])
    elif args[0] == "uninstall":
        _run_uninstall()
    elif args[0] == "update":
        _run_update()
    else:
        console.print(f"[red]Unknown command:[/] {args[0]}")
        console.print("Usage: finarg [init|chat|config|update|uninstall|version]")
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

    # Copy bundled skills (only if not already present)
    _install_bundled_skills()

    env_lines: list[str] = []

    # Step 1: LLM Provider
    console.print("[bold #4fc3f7]1/3 LLM Provider[/]")
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
    console.print("[bold #4fc3f7]2/3 Ripio Trade (optional)[/]")
    console.print("  [#8892b0]Enables wallet management and crypto transfers.[/]")
    console.print("  [#8892b0]Get your keys at: https://app.ripio.com/trade/api[/]")

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

    console.print()

    # Step 3: AFIP/ARCA (SIRADIG)
    console.print("[bold #4fc3f7]3/3 AFIP/ARCA — SIRADIG (optional)[/]")
    console.print("  [#8892b0]Enables automatic tax deduction loading (Ganancias).[/]")

    has_afip = Confirm.ask("  Do you want to configure AFIP credentials?", default=False)
    if has_afip:
        afip_cuit = Prompt.ask("  AFIP_CUIT (sin guiones)")
        if afip_cuit:
            env_lines.append(f"AFIP_CUIT={afip_cuit}")
            console.print(f"  [#00ff88]\u2713 CUIT saved[/]")

        console.print()
        console.print("  [#8892b0]La clave fiscal permite login automático en SIRADIG.[/]")
        console.print("  [#8892b0]Sin ella, se abre un browser visible para que logees manualmente.[/]")
        has_clave = Confirm.ask("  Save Clave Fiscal?", default=False)
        if has_clave:
            afip_clave = Prompt.ask("  AFIP_CLAVE_FISCAL")
            if afip_clave:
                env_lines.append(f"AFIP_CLAVE_FISCAL={afip_clave}")
                console.print("  [#00ff88]\u2713 Clave Fiscal saved[/]")
        else:
            console.print("  [#8892b0]OK. El agente te pedirá logear manualmente cuando uses SIRADIG.[/]")
    else:
        console.print("  [#8892b0]Skipped. You can configure later with finarg config set[/]")

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


def _run_config(args: list[str]) -> None:
    """View or edit configuration."""
    if not args or args[0] == "show":
        # Show current config
        console.print()
        console.print("[bold #4fc3f7]Config[/]", f"({CONFIG_FILE})")
        if CONFIG_FILE.exists():
            console.print(CONFIG_FILE.read_text())
        else:
            console.print("[#8892b0]No config file. Run `finarg init`.[/]")

        console.print("[bold #4fc3f7]Secrets[/]", f"({ENV_FILE})")
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    masked = value[:4] + "..." + value[-4:] if len(value) > 12 else "****"
                    console.print(f"  {key}={masked}")
                else:
                    console.print(f"  {line}")
        else:
            console.print("[#8892b0]No secrets file. Run `finarg init`.[/]")
        console.print()

    elif args[0] == "edit":
        # Open in editor
        editor = os.getenv("EDITOR", "nano")
        if len(args) > 1 and args[1] == "secrets":
            os.execvp(editor, [editor, str(ENV_FILE)])
        else:
            os.execvp(editor, [editor, str(CONFIG_FILE)])

    elif args[0] == "set":
        # Quick set: finarg config set KEY=VALUE (in .env)
        if len(args) < 2 or "=" not in args[1]:
            console.print("Usage: finarg config set KEY=VALUE")
            console.print("Example: finarg config set RIPIO_TRADE_API_KEY=your-key")
            return

        key, value = args[1].split("=", 1)
        key = key.upper()

        # Read existing .env
        env_lines: list[str] = []
        replaced = False
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                if line.startswith(f"{key}="):
                    env_lines.append(f"{key}={value}")
                    replaced = True
                else:
                    env_lines.append(line)

        if not replaced:
            env_lines.append(f"{key}={value}")

        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENV_FILE.write_text("\n".join(env_lines) + "\n")
        ENV_FILE.chmod(0o600)

        masked = value[:4] + "..." + value[-4:] if len(value) > 12 else "****"
        console.print(f"[#00ff88]\u2713[/] Set {key}={masked}")

    else:
        console.print("Usage:")
        console.print("  finarg config              Show current config")
        console.print("  finarg config edit          Edit config.yaml in $EDITOR")
        console.print("  finarg config edit secrets  Edit .env in $EDITOR")
        console.print("  finarg config set KEY=VAL   Set a secret in .env")


def _is_pipx_install() -> bool:
    """Detect if finarg was installed via pipx."""
    import shutil
    import subprocess

    # Check 1: running from a pipx venv
    if "pipx/venvs" in sys.executable:
        return True

    # Check 2: pipx knows about finarg
    if shutil.which("pipx"):
        result = subprocess.run(
            ["pipx", "list", "--short"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and "finarg" in result.stdout:
            return True

    return False


def _run_update() -> None:
    """Update Finarg to the latest version."""
    import shutil
    import subprocess

    from finarg import __version__

    console.print(f"  Current version: [bold]{__version__}[/]")
    console.print("  Updating from GitHub...")

    repo_url = "git+https://github.com/Gantalf/finarg.git"

    if _is_pipx_install() and shutil.which("pipx"):
        console.print("  [#8892b0]Detected pipx install[/]")
        result = subprocess.run(
            ["pipx", "install", "--force", repo_url],
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--force-reinstall", repo_url],
            capture_output=True,
            text=True,
        )

    if result.returncode == 0:
        console.print("  [#00ff88]\u2713 Updated successfully.[/] Restart finarg to use the new version.")
    else:
        error_lines = result.stderr.strip().splitlines() if result.stderr else []
        last_line = error_lines[-1] if error_lines else "unknown error"
        console.print(f"  [#ff4444]\u2717 Update failed:[/] {last_line}")
        console.print("  Try manually: pipx install --force git+https://github.com/Gantalf/finarg.git")


def _run_uninstall() -> None:
    """Completely remove Finarg: config, data, and the package itself."""
    import shutil
    import subprocess

    console.print()
    console.print(
        Panel(
            "[bold #ff4444]Uninstall Finarg[/]\n"
            "[#8892b0]This will remove all config, secrets, skills, and data.[/]",
            border_style="#ff4444",
            padding=(1, 4),
        )
    )
    console.print()

    # Show what will be deleted
    if FINARG_HOME.exists():
        console.print(f"  [#ff4444]\u2717[/] Delete {FINARG_HOME}/ (config, secrets, skills, sessions)")
    else:
        console.print(f"  [#8892b0]-[/] {FINARG_HOME}/ not found")

    console.print(f"  [#ff4444]\u2717[/] Uninstall finarg Python package")
    console.print()

    confirm = Confirm.ask("  Are you sure?", default=False)
    if not confirm:
        console.print("  [#8892b0]Cancelled.[/]")
        return

    # Delete ~/.finarg/
    if FINARG_HOME.exists():
        shutil.rmtree(FINARG_HOME)
        console.print(f"  [#00ff88]\u2713[/] Deleted {FINARG_HOME}/")

    # Uninstall the package (detect pipx vs pip)
    console.print("  Uninstalling finarg package...")
    if _is_pipx_install() and shutil.which("pipx"):
        subprocess.run(["pipx", "uninstall", "finarg"], capture_output=True)
    else:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "finarg", "-y"],
            capture_output=True,
        )
    console.print(f"  [#00ff88]\u2713[/] Package uninstalled")

    console.print()
    console.print(
        Panel(
            "[bold #00ff88]Finarg completely removed.[/]\n\n"
            "[#8892b0]Note: pipx may have added ~/.local/bin to your PATH.\n"
            "To remove it, edit ~/.bashrc or ~/.zshrc and remove the pipx line.[/]\n\n"
            "To reinstall:\n"
            "  curl -fsSL https://raw.githubusercontent.com/Gantalf/finarg/main/scripts/install.sh | bash",
            border_style="#00ff88",
            padding=(1, 4),
        )
    )


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
    from finarg.constants import DB_FILE, FINARG_HOME, SKILLS_DIR
    from finarg.tools.registry import registry

    # Load built-in tools (matches Hermes _discover_tools pattern)
    from finarg.tools.wallet import register_wallet_tools
    from finarg.tools.transfer import register_transfer_tools
    from finarg.tools.market_data import register_market_data_tools
    from finarg.tools.web import register_web_tools
    from finarg.tools.browser import register_browser_tools
    from finarg.tools.terminal import register_terminal_tools
    from finarg.tools.file_tools import register_file_tools
    from finarg.tools.skill_manager import register_skill_manager_tools
    from finarg.tools.skills import register_skills_tools

    register_wallet_tools()
    register_transfer_tools()
    register_market_data_tools()
    register_web_tools()
    register_browser_tools()
    register_terminal_tools()
    register_file_tools()
    register_skill_manager_tools()
    register_skills_tools()

    # SIRADIG
    from finarg.tools.siradig import register_siradig_tools
    register_siradig_tools()

    # Memory
    from finarg.tools.memory import MemoryStore, register_memory_tools, set_memory_store

    memory_dir = FINARG_HOME / "memories"
    memory_store = MemoryStore(memory_dir)
    memory_store.load_from_disk()
    set_memory_store(memory_store)
    register_memory_tools()

    # Build the right provider based on config
    llm_provider = _build_provider(config.model.provider, api_key, config.model.default)

    # Visual analysis (uses the same LLM provider)
    from finarg.tools.visual import set_visual_provider, register_visual_tools
    set_visual_provider(llm_provider)
    register_visual_tools()

    session_store = SessionStore(DB_FILE)

    return FinargAgent(
        config=config,
        provider=llm_provider,
        registry=registry,
        session_store=session_store,
        memory_store=memory_store,
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
