<p align="center">
  <br>
  <b style="font-size: 48px;">FINARG</b>
  <br>
  <em>AI-Powered Financial Agent for Argentina & LATAM</em>
  <br><br>
  <a href="https://github.com/Gantalf/finarg/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/Gantalf/finarg"><img src="https://img.shields.io/badge/Python-3.11+-green?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://github.com/Gantalf/finarg/issues"><img src="https://img.shields.io/badge/Issues-GitHub-red?style=for-the-badge&logo=github" alt="Issues"></a>
</p>

**An AI agent that manages your crypto wallet, checks exchange rates, executes transfers, and builds its own new capabilities on demand.** Talk to it in natural language — it calls APIs, shows you the data, and asks for confirmation before touching your money.

<table>
<tr><td><b>Wallet management</b></td><td>Check balances (trade + wallet), get deposit addresses, and send crypto via Ripio API.</td></tr>
<tr><td><b>Argentine market data</b></td><td>Dollar oficial, blue, MEP from BCRA. Crypto tickers from Ripio. Always know the real rate.</td></tr>
<tr><td><b>Safe by design</b></td><td>Every transfer requires explicit confirmation. The agent shows you amount, address, and fees before executing.</td></tr>
<tr><td><b>Self-extending</b></td><td>The agent researches APIs, creates skills (SKILL.md documents), and executes scripts — learning new capabilities without code changes.</td></tr>
<tr><td><b>Persistent memory</b></td><td>Remembers your name, preferences, and context across sessions. Never asks the same thing twice.</td></tr>
<tr><td><b>Bundled skills</b></td><td>Comes with ARCA (ex AFIP) electronic invoicing skill pre-installed. Just configure your certificates.</td></tr>
<tr><td><b>Any LLM provider</b></td><td>Anthropic (Claude), OpenAI, Moonshot/Kimi — switch providers without changing code.</td></tr>
</table>

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/Gantalf/finarg/main/scripts/install.sh | bash
```

Works on Linux, macOS, and WSL2. The installer handles Python, Node.js (for browser tools), pip, and the `finarg` command.

> **Windows:** Native Windows is not supported. Please install [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) and run the command above.

**Or install manually:**

```bash
pip install git+https://github.com/Gantalf/finarg.git
```

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
finarg init         # setup wizard — configure API keys
finarg              # start chatting
```

---

## Commands

```bash
finarg                        # Start chatting with the agent
finarg init                   # Setup wizard (LLM + Ripio keys)
finarg config                 # Show current config and secrets (masked)
finarg config set KEY=VALUE   # Set a secret in .env
finarg config edit            # Edit config.yaml in $EDITOR
finarg config edit secrets    # Edit .env in $EDITOR
finarg update                 # Update to latest version from GitHub
finarg uninstall              # Completely remove Finarg (config, data, package)
finarg version                # Check installed version
```

On first launch, `finarg init` walks you through:

1. **LLM Provider** — Choose Anthropic, OpenAI, or Moonshot and enter your API key
2. **Ripio Trade** (optional) — Enter your API key + secret for wallet and transfer features

Without Ripio keys, you still get AI chat + BCRA dollar rates (public API, no key needed).

---

## Built-in Tools (23)

| Toolset | Tool | What it does |
|---------|------|-------------|
| **wallet** | `get_balances` | Crypto balances in your Ripio Trade account |
| | `get_deposit_address` | Deposit address for any supported coin |
| **transfer** | `withdraw_crypto` | Send crypto to an external address (with confirmation) |
| **market_data** | `get_ticker` | Price and 24h stats for any trading pair |
| | `get_dolar_rates` | Argentine dollar rates from BCRA (oficial, blue, MEP) |
| **terminal** | `terminal` | Execute shell commands and scripts |
| **file** | `read_file` | Read a file with line numbers and pagination |
| | `write_file` | Write content to a file |
| | `patch_file` | Find-and-replace in a file |
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
| **memory** | `memory` | Save/update/remove persistent facts across sessions |

---

## Skills

The agent can **create its own knowledge** when you ask:

```
You: "Investigá cómo transferir de mi wallet a trade en Ripio y creá un skill"

Finarg: → web_search("ripio api wallet to trade transfer")
        → read_webpage(endpoint docs)
        → skill_manage(create, "ripio-wallet-transfer", instructions)
        ✓ Skill created at ~/.finarg/skills/ripio-wallet-transfer/SKILL.md

        Next time you ask, I'll read the skill and execute it.
```

Skills are SKILL.md documents (YAML frontmatter + markdown instructions). They capture **how to do a task**: which endpoint to call, what parameters to use, what to watch out for. The agent reads the skill and executes scripts via `terminal`.

```
~/.finarg/skills/
├── arca-facturacion/          # Bundled — ARCA/AFIP electronic invoicing
│   └── SKILL.md
├── ripio-wallet-transfer/     # Created by agent
│   └── SKILL.md
└── my-custom-skill/
    ├── SKILL.md
    └── references/
        └── api-docs.md
```

### Bundled skills

These come pre-installed with Finarg:

| Skill | What it does | Prerequisites |
|-------|-------------|---------------|
| **arca-facturacion** | ARCA (ex AFIP) electronic invoicing via [@ramiidv/arca-sdk](https://github.com/ramiidv/arca-facturacion). Factura A/B/C/E, NC, ND, exportación, padrón, QR. | `ARCA_CUIT`, `ARCA_CERT_PATH`, `ARCA_KEY_PATH` |

Skills with missing prerequisites show a warning. The agent tells you exactly what to configure:

```bash
finarg config set ARCA_CUIT=20123456789
finarg config set ARCA_CERT_PATH=/path/to/cert.crt
finarg config set ARCA_KEY_PATH=/path/to/key.key
```

---

## Memory

The agent remembers things across sessions:

- **User profile** (`~/.finarg/memories/USER.md`) — your name, location, preferences
- **Agent notes** (`~/.finarg/memories/MEMORY.md`) — environment facts, API quirks, lessons learned

The agent saves to memory proactively (when you tell it your name, correct it, or share a preference). On the next session, it already knows.

```
Session 1:
  You: "Me llamo Luciano, estoy en Buenos Aires"
  Finarg: (saves to USER.md)

Session 2:
  You: "Cómo me llamo?"
  Finarg: "Te llamás Luciano."
```

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
│            ToolRegistry (23 tools)       │
├────────────────┬────────────────────────┤
│  Built-in      │  Skills (SKILL.md)     │
│  · Ripio API   │  ~/.finarg/skills/*/   │
│  · BCRA API    │  Created by agent      │
│  · Terminal    │  or bundled            │
│  · File ops    │                        │
│  · Web/Browser │                        │
│  · Memory      │                        │
├────────────────┴────────────────────────┤
│  Persistence                             │
│  · SQLite (sessions)                     │
│  · MEMORY.md + USER.md (memory)          │
└─────────────────────────────────────────┘
```

**Key design decisions:**

- **SOUL.md** — personality and rules only, no technical guidance
- **prompt_builder.py** — technical guidance as constants: tool usage, skills guidance, memory guidance, script execution patterns, tool-use enforcement
- **Skills = documents** — SKILL.md with YAML frontmatter, not executable code. The agent reads instructions and executes via `terminal`
- **Memory** — two files (USER.md + MEMORY.md) with char limits, frozen snapshot for prompt injection (prefix cache stability)
- **Tool registry** — tools self-register at import time with availability checks
- **Authenticated clients** — HMAC-SHA256 signing for Ripio API, reusable from skills via `get_trade_client()`

---

## Configuration

All data lives in `~/.finarg/`:

```
~/.finarg/
├── config.yaml          # Model, API settings
├── .env                 # API keys (never committed)
├── skills/              # Skills (SKILL.md documents)
├── memories/            # Persistent memory
│   ├── MEMORY.md        # Agent notes
│   └── USER.md          # User profile
└── finarg.db            # SQLite (session history)
```

### Config file (`~/.finarg/config.yaml`)

```yaml
model:
  default: claude-sonnet-4-20250514
  provider: anthropic    # or: openai, moonshot

agent:
  max_turns: 30

apis:
  ripio_trade:
    enabled: true
    rate_limit: 1.0
  bcra:
    enabled: true
```

### Environment variables (`~/.finarg/.env`)

```env
# LLM Provider (required — one of these)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
MOONSHOT_API_KEY=sk-...

# Ripio Trade (optional — enables wallet + transfers)
RIPIO_TRADE_API_KEY=your-key
RIPIO_TRADE_API_SECRET=your-secret

# ARCA invoicing (optional — enables facturacion skill)
ARCA_CUIT=20123456789
ARCA_CERT_PATH=/path/to/cert.crt
ARCA_KEY_PATH=/path/to/key.key
```

---

## Project context files

Create a `.finarg.md` file in any directory to give the agent project-specific context. The agent reads it automatically when you run `finarg` from that directory.

```markdown
# My trading setup
- Ripio account has BTC, ETH, and USDC
- Max 100 USDC per transaction
- Transfers go to wallet 0x1234...
```

Also supports `AGENTS.md` and `CLAUDE.md`. Files are capped at 20,000 chars.

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
- Bundled skill packs (collections of SKILL.md for common workflows)
- Bug fixes and documentation improvements

---

## Roadmap

The agent can build its own features via skills, but these are planned as built-in:

- [ ] Trading (limit/market orders, swaps)
- [ ] Fiat on/off ramp (buy/sell crypto with ARS)
- [ ] Wire transfers and QR payments
- [ ] Scheduled/recurring payments
- [ ] Telegram and WhatsApp gateway
- [ ] MercadoPago integration
- [ ] Portfolio analytics and PnL tracking

---

## License

**MIT** — Free to use, modify, and distribute. See [LICENSE](LICENSE).

Built by [Gantalf](https://github.com/Gantalf).
