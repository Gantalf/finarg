<p align="center">
  <br>
  <b style="font-size: 48px;">FINARG</b>
  <br>
  <em>AI-Powered Financial Agent for Argentina & LATAM</em>
  <br><br>
  <a href="https://github.com/Gantalf/finarg/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: AGPL-3.0"></a>
  <a href="https://github.com/Gantalf/finarg"><img src="https://img.shields.io/badge/Python-3.11+-green?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://github.com/Gantalf/finarg/issues"><img src="https://img.shields.io/badge/Issues-GitHub-red?style=for-the-badge&logo=github" alt="Issues"></a>
</p>

**An AI agent that manages your crypto wallet, checks exchange rates, executes transfers, and builds its own new capabilities on demand.** Talk to it in natural language — it calls APIs, shows you the data, and asks for confirmation before touching your money.

It's not just a chatbot with tools. It's a **self-extending agent**: ask it to learn a new skill (trading, invoicing, payments) and it writes the code, registers the tool, and makes it available — all in one conversation.

<table>
<tr><td><b>Wallet management</b></td><td>Check balances, get deposit addresses, and send crypto — all through natural language via Ripio Trade API.</td></tr>
<tr><td><b>Argentine market data</b></td><td>Dollar oficial, blue, MEP from BCRA. Crypto tickers from Ripio. Always know the real rate.</td></tr>
<tr><td><b>Safe by design</b></td><td>Every transfer requires explicit confirmation. The agent shows you amount, address, and fees before executing anything.</td></tr>
<tr><td><b>Self-extending skills</b></td><td>Ask it to "create a skill for limit orders" — it writes a Python tool, validates it, hot-loads it into the registry. No restart needed.</td></tr>
<tr><td><b>Clean terminal chat</b></td><td>Rich formatted output with markdown, tool call indicators, and streaming responses.</td></tr>
<tr><td><b>Session persistence</b></td><td>SQLite-backed conversation history and transaction audit log. Pick up where you left off.</td></tr>
<tr><td><b>Any LLM provider</b></td><td>Anthropic (Claude), OpenAI, Moonshot/Kimi — switch providers without changing code.</td></tr>
</table>

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/Gantalf/finarg/main/scripts/install.sh | bash
```

Works on Linux, macOS, and WSL2. The installer handles Python, pip, and the `finarg` command. No prerequisites except git.

> **Windows:** Native Windows is not supported. Please install [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) and run the command above.

**Or install manually:**

```bash
pip install finarg          # from PyPI (when published)
pip install git+https://github.com/Gantalf/finarg.git   # from GitHub
```

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
finarg init         # setup wizard — configure API keys
finarg              # start chatting
```

---

## Getting Started

```bash
finarg              # Start chatting with the agent
finarg init         # Interactive setup wizard (LLM + Ripio keys)
finarg config       # Show current config and secrets (masked)
finarg config set KEY=VALUE   # Set a secret in .env
finarg config edit            # Edit config.yaml in $EDITOR
finarg config edit secrets    # Edit .env in $EDITOR
finarg uninstall    # Completely remove Finarg (config, data, package)
finarg version      # Check installed version
```

On first launch, `finarg init` walks you through:

1. **LLM Provider** — Choose Anthropic, OpenAI, or Moonshot and enter your API key
2. **Ripio Trade** (optional) — Enter your API key + secret for wallet and transfer features

Without Ripio keys, you still get AI chat + BCRA dollar rates (public API, no key needed).

---

## What Can It Do?

### Built-in Tools (17)

| Toolset | Tool | What it does |
|---------|------|-------------|
| **wallet** | `get_balances` | Show all crypto balances in your Ripio wallet |
| | `get_deposit_address` | Get a deposit address for any supported coin |
| **transfer** | `withdraw_crypto` | Send crypto to an external address (with confirmation) |
| **market_data** | `get_ticker` | Current price and 24h stats for any trading pair |
| | `get_dolar_rates` | Argentine dollar rates from BCRA (oficial, blue, MEP) |
| **web** | `web_search` | Search the web via DuckDuckGo (no API key needed) |
| | `read_webpage` | Fetch a URL and convert to clean markdown |
| **browser** | `browser_navigate` | Open a URL in headless Chromium |
| | `browser_snapshot` | Get page accessibility tree (elements with refs) |
| | `browser_click` | Click an element by ref (e.g. @e5) |
| | `browser_type` | Type text into an input field |
| | `browser_scroll` | Scroll the page up or down |
| | `browser_back` | Navigate back |
| | `browser_close` | Close the browser session |
| **skills** | `create_skill` | Write and register a new tool on the fly |
| | `list_skills` | Show all user-created skills |
| | `delete_skill` | Remove a skill |

### Self-Extending Skills

This is the killer feature. The agent can **create its own tools** when you ask:

```
You: "Create a skill to place limit orders on Ripio"

Finarg: I'll create a skill called `ripio_limit_orders`...
        ✓ Validated syntax
        ✓ Written to ~/.finarg/skills/ripio_limit_orders.py
        ✓ Hot-loaded into registry

        You can now say "place a limit buy for 0.01 BTC at $65,000"
```

Skills are plain Python files in `~/.finarg/skills/`. They persist across sessions and load automatically on startup. The agent validates syntax before saving, and you can review/edit them manually.

---

## Architecture

```
┌─────────────────────────────────────────┐
│            Terminal UI (Textual)         │
│  Ticker · Balances · Chat · Charts      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│            FinargAgent                   │
│  LLM call → tool calls → execute → loop │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│            ToolRegistry                  │
│  Built-in tools + hot-loaded skills      │
├────────────────┬────────────────────────┤
│  API Clients   │  User Skills (SKILL.md) │
│  · Ripio Trade │  ~/.finarg/skills/*/    │
│  · BCRA        │  Auto-created by agent  │
├────────────────┴────────────────────────┤
│  SQLite (sessions + transaction log)     │
└─────────────────────────────────────────┘
```

**Key design decisions:**

- **Fully async** — httpx + asyncio throughout
- **Tool registry pattern** — tools self-register at import time
- **Skills = documents** — SKILL.md files with YAML frontmatter (like Hermes), not executable code
- **HMAC-SHA256 auth** — Ripio Trade API signing implemented correctly per their spec
- **Confirmation flow** — withdraw_crypto never executes without explicit user approval (enforced at prompt level via SOUL.md)
- **Provider abstraction** — swap between Anthropic, OpenAI, or any OpenAI-compatible endpoint

---

## Configuration

All config lives in `~/.finarg/`:

```
~/.finarg/
├── config.yaml          # Model, API settings
├── .env                 # API keys (never committed)
├── skills/              # Skills (SKILL.md documents, created by agent)
└── finarg.db            # SQLite (sessions + transaction log)
```

### Config file (`~/.finarg/config.yaml`)

```yaml
model:
  default: claude-sonnet-4-20250514
  provider: anthropic

agent:
  max_turns: 30

apis:
  ripio_trade:
    enabled: true
    rate_limit: 1.0
  bcra:
    enabled: true

tui:
  theme: dark
  ticker_pairs: [BTC_USDT, ETH_USDT, USDT_ARS]
  refresh_interval: 30
```

### Environment variables (`~/.finarg/.env`)

```env
ANTHROPIC_API_KEY=sk-ant-...
RIPIO_TRADE_API_KEY=your-key
RIPIO_TRADE_API_SECRET=your-secret
```

---

## Project context files

You can create a `.finarg.md` file in any directory to give the agent project-specific context. When you run `finarg` from that directory, the agent reads it automatically.

Example `.finarg.md`:

```markdown
# My trading setup
- Ripio account has BTC, ETH, and USDC
- Max 100 USDC per transaction
- Transfers go to wallet 0x1234...
```

Also supports `AGENTS.md` and `CLAUDE.md` (for compatibility with other tools). Files are capped at 20,000 chars.

---

## Contributing

Contributions welcome! Clone and install in dev mode:

```bash
git clone https://github.com/Gantalf/finarg.git
cd finarg
pip install -e ".[dev]"
finarg version
```

---

## Roadmap

The agent can build its own features via skills, but these are planned as built-in:

- [ ] Trading (limit/market orders, swaps via Ripio B2B)
- [ ] Fiat on/off ramp (buy/sell crypto with ARS)
- [ ] Wire transfers and QR payments
- [ ] AFIP/ARCA electronic invoicing
- [ ] Scheduled/recurring payments
- [ ] Telegram and WhatsApp gateway
- [ ] MercadoPago integration
- [ ] Portfolio analytics and PnL tracking

---

## License

**MIT** — Free to use, modify, and distribute. See [LICENSE](LICENSE).

Built by [Gantalf](https://github.com/Gantalf).
