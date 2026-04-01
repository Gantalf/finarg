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

### Built-in Tools (22)

| Toolset | Tool | What it does |
|---------|------|-------------|
| **wallet** | `get_balances` | Show all crypto balances in your Ripio Trade account |
| | `get_deposit_address` | Get a deposit address for any supported coin |
| **transfer** | `withdraw_crypto` | Send crypto to an external address (with confirmation) |
| **market_data** | `get_ticker` | Current price and 24h stats for any trading pair |
| | `get_dolar_rates` | Argentine dollar rates from BCRA (oficial, blue, MEP) |
| **terminal** | `terminal` | Execute shell commands and scripts |
| **file** | `read_file` | Read a file with line numbers and pagination |
| | `write_file` | Write content to a file |
| | `patch` | Find-and-replace in a file |
| | `search_files` | Search file contents with regex |
| **web** | `web_search` | Search the web via DuckDuckGo (no API key needed) |
| | `read_webpage` | Fetch a URL and convert to clean markdown |
| **browser** | `browser_navigate` | Open a URL in headless Chromium |
| | `browser_snapshot` | Get page accessibility tree (elements with refs) |
| | `browser_click` | Click an element by ref (e.g. @e5) |
| | `browser_type` | Type text into an input field |
| | `browser_scroll` | Scroll the page up or down |
| | `browser_back` | Navigate back |
| | `browser_close` | Close the browser session |
| **skills** | `skills_list` | List all available skills with descriptions |
| | `skill_view` | Load full instructions from a skill |
| | `skill_manage` | Create, edit, patch, or delete skills |

### Self-Extending Skills

This is the killer feature. The agent can **create its own knowledge** when you ask:

```
You: "Investigá cómo transferir de mi wallet a trade en Ripio y creá un skill"

Finarg: → web_search("ripio api wallet to trade transfer")
        → read_webpage(endpoint docs)
        → skill_manage(create, "ripio-wallet-transfer", instructions)
        ✓ Skill created at ~/.finarg/skills/ripio-wallet-transfer/SKILL.md

        Next time you ask, I'll read the skill and execute it.
```

Skills are SKILL.md documents (YAML frontmatter + markdown) — not code. They capture **how to do a task**: which endpoint to call, what parameters to use, what to watch out for. The agent reads the skill and executes scripts via `terminal` following the instructions.

```
~/.finarg/skills/
├── ripio-wallet-transfer/
│   └── SKILL.md           # Instructions for wallet ↔ trade transfers
├── mercadopago-qr/
│   ├── SKILL.md           # How to process QR payments
│   └── references/
│       └── api-docs.md    # Supporting documentation
```

Skills persist across sessions. On startup, the agent sees an index of all available skills and can load any of them with `skill_view`.

---

## Architecture

```
┌─────────────────────────────────────────┐
│            Chat Interface               │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│            FinargAgent                   │
│  LLM call → tool calls → execute → loop │
│                                          │
│  SOUL.md (personality)                   │
│  prompt_builder.py (technical guidance)  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│            ToolRegistry (22 tools)       │
├────────────────┬────────────────────────┤
│  Built-in      │  Skills (SKILL.md)     │
│  · Ripio API   │  ~/.finarg/skills/*/   │
│  · BCRA API    │  Created by the agent  │
│  · Terminal    │  Read on demand via     │
│  · File ops    │  skill_view            │
│  · Web/Browser │                        │
├────────────────┴────────────────────────┤
│  SQLite (sessions + transaction log)     │
└─────────────────────────────────────────┘
```

**Architecture follows [Hermes Agent](https://github.com/nousresearch/hermes-agent):**

- **SOUL.md** — personality only (like Hermes)
- **prompt_builder.py** — technical guidance as constants: tool usage, skills guidance, script execution patterns, tool-use enforcement (like Hermes)
- **Skills = SKILL.md documents** — YAML frontmatter + markdown instructions, not executable code (like Hermes)
- **Tool registry** — tools self-register at import time with check_fn availability checks (like Hermes)
- **Terminal** — agent executes scripts via subprocess, reusing authenticated API clients (like Hermes)
- **Provider abstraction** — Anthropic, OpenAI, or any OpenAI-compatible endpoint (Moonshot/Kimi)

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

Contributions welcome! Fork the repo, create a branch, and open a PR.

```bash
git clone https://github.com/Gantalf/finarg.git
cd finarg
pip install -e ".[dev]"
finarg version
```

### How to contribute

1. **Fork** the repo on GitHub
2. **Clone** your fork: `git clone https://github.com/YOUR_USER/finarg.git`
3. **Create a branch**: `git checkout -b my-feature`
4. **Make changes** and test locally
5. **Push** and open a **Pull Request** against `main`

### Ideas for contributions

- New API clients (MercadoPago, Binance, Bitso)
- New built-in tools
- Skills packs (collections of SKILL.md for common workflows)
- Bug fixes and documentation improvements

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
