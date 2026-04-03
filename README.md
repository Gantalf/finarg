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

**An AI agent that manages your crypto wallet, checks exchange rates, executes transfers, reads invoices, loads tax deductions, and builds its own new capabilities on demand.** Talk to it in natural language — it calls APIs, automates browsers, and asks for confirmation before touching your money.

<table>
<tr><td><b>Wallet management</b></td><td>Check balances (trade + wallet), transfer between accounts, get deposit addresses, and send crypto via Ripio API.</td></tr>
<tr><td><b>Argentine market data</b></td><td>Dollar oficial, blue, MEP from BCRA. Crypto tickers from Ripio. Always know the real rate.</td></tr>
<tr><td><b>Invoice reading</b></td><td>Give the agent a PDF or image of an invoice — it reads it visually and extracts all fields (CUIT, amount, date, etc.).</td></tr>
<tr><td><b>SIRADIG automation</b></td><td>Load tax deductions (Ganancias) in ARCA/AFIP automatically. Login, navigate, fill forms, save — all in one command.</td></tr>
<tr><td><b>Safe by design</b></td><td>Every transfer requires explicit confirmation. The agent shows you amount, address, and fees before executing.</td></tr>
<tr><td><b>Self-extending</b></td><td>The agent researches APIs, creates skills (SKILL.md documents), and executes scripts — learning new capabilities without code changes.</td></tr>
<tr><td><b>Persistent memory</b></td><td>Remembers your name, preferences, and context across sessions. Never asks the same thing twice.</td></tr>
<tr><td><b>Any LLM provider</b></td><td>Anthropic (Claude), OpenAI, Moonshot/Kimi — switch providers without changing code.</td></tr>
</table>

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/Gantalf/finarg/main/scripts/install.sh | bash
```

Works on Linux, macOS, and WSL2. The installer handles Python, Node.js, Playwright, and the `finarg` command.

> **Windows:** Native Windows is not supported. Please install [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) and run the command above.

**Or install manually:**

```bash
pip install git+https://github.com/Gantalf/finarg.git
python -m playwright install chromium
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
finarg init                   # Setup wizard (LLM + Ripio + AFIP keys)
finarg config                 # Show current config and secrets (masked)
finarg config set KEY=VALUE   # Set a secret in .env
finarg config edit            # Edit config.yaml in $EDITOR
finarg config edit secrets    # Edit .env in $EDITOR
finarg update                 # Update to latest version from GitHub
finarg uninstall              # Completely remove Finarg (config, data, package)
finarg version                # Check installed version
```

---

## Built-in Tools (32)

| Toolset | Tool | What it does |
|---------|------|-------------|
| **wallet** | `get_balances` | Crypto balances in your Ripio Trade account |
| | `get_wallet_balances` | Crypto balances in your Ripio Wallet (app) |
| | `get_deposit_address` | Deposit address for any supported coin |
| | `wallet_transfer` | Move funds between Wallet and Trade (both directions) |
| **transfer** | `withdraw_crypto` | Send crypto to an external wallet address (with confirmation) |
| **market_data** | `get_ticker` | Price and 24h stats for any trading pair |
| | `get_dolar_rates` | Argentine dollar rates from BCRA (oficial, blue, MEP) |
| | `get_currencies` | List available cryptos with networks, min amounts, memo/tag requirements |
| **terminal** | `terminal` | Execute shell commands and scripts |
| **file** | `read_file` | Read a file with line numbers and pagination |
| | `write_file` | Write content to a file |
| | `patch_file` | Find-and-replace in a file |
| | `search_files` | Search file contents with regex |
| | `analyze_document` | Read a PDF or image visually using the LLM (invoices, receipts, etc.) |
| **web** | `web_search` | Search the web via DuckDuckGo (no API key needed) |
| | `read_webpage` | Fetch a URL and convert to clean markdown |
| **browser** | `browser_navigate` | Open a URL in Chromium (supports headed mode + session persistence) |
| | `browser_snapshot` | Get page accessibility tree (elements with refs) |
| | `browser_click` | Click an element by ref or CSS selector |
| | `browser_fill` | Clear and fill an input field |
| | `browser_select` | Select a dropdown option |
| | `browser_type` | Type text into an element |
| | `browser_wait` | Wait for an element or milliseconds |
| | `browser_scroll` | Scroll the page up or down |
| | `browser_back` | Navigate back |
| | `browser_close` | Close the browser session |
| **siradig** | `siradig_login` | Login to AFIP and navigate to SIRADIG (deterministic, one call) |
| | `siradig_add_deduction` | Fill and save a tax deduction form (deterministic, one call) |
| **skills** | `skills_list` | List all available skills with descriptions |
| | `skill_view` | Load full instructions from a skill |
| | `skill_manage` | Create, edit, patch, or delete skills |
| **memory** | `memory` | Save/update/remove persistent facts across sessions |

---

## SIRADIG — Tax Deductions

Load Ganancias deductions automatically:

```
You: "deducime ~/factura.pdf como indumentaria en siradig"

Finarg: → analyze_document (reads invoice visually)
        → Shows extracted data, asks confirmation
        → siradig_login (opens browser, logs into AFIP, navigates to SIRADIG)
        → siradig_add_deduction (fills form, saves)
        ✓ Deduction saved
```

The SIRADIG tools use Playwright with a visible browser window. Session is persisted — login once, reuse across sessions.

Configure credentials:
```bash
finarg config set AFIP_CUIT=20XXXXXXXXX
finarg config set AFIP_CLAVE_FISCAL=yourpassword
```

Supported deduction categories: gastos médicos, indumentaria y equipamiento, alquiler, seguros, servicio doméstico, donaciones, cuotas sindicales.

---

## Invoice Reading

Give the agent any PDF or image and it reads it visually:

```
You: "analizá ~/factura.pdf"

Finarg: → analyze_document (sends file to LLM vision)
        CUIT: 30-12345678-9
        Razón social: EMPRESA SA
        Factura B, PV 0001, Nro 00012345
        Fecha: 01/03/2026
        Monto: $15.000
```

Supports: PDF, JPEG, PNG, GIF, WebP. Works with all three LLM providers.

---

## Skills

The agent can **create its own knowledge** when you ask:

```
You: "Investigá cómo transferir de mi wallet a trade en Ripio y creá un skill"

Finarg: → web_search + read_webpage (researches API docs)
        → skill_manage(create, "ripio-wallet-transfer", instructions)
        ✓ Skill created at ~/.finarg/skills/ripio-wallet-transfer/SKILL.md
```

Skills are SKILL.md documents (YAML frontmatter + markdown instructions). They persist across sessions.

### Bundled skills

| Skill | What it does | Prerequisites |
|-------|-------------|---------------|
| **arca-facturacion** | Electronic invoicing via [@ramiidv/arca-sdk](https://github.com/ramiidv/arca-facturacion) | `ARCA_CUIT`, `ARCA_CERT_PATH`, `ARCA_KEY_PATH` |
| **siradig-deducciones** | Tax deduction form reference (selectors, mappings) | `AFIP_CUIT` |

---

## Memory

The agent remembers things across sessions:

- **User profile** (`~/.finarg/memories/USER.md`) — your name, location, preferences
- **Agent notes** (`~/.finarg/memories/MEMORY.md`) — environment facts, API quirks, lessons learned

```
Session 1:  You: "Me llamo Luciano, estoy en Buenos Aires"
Session 2:  You: "Cómo me llamo?"  →  "Te llamás Luciano."
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
│            ToolRegistry (32 tools)       │
├────────────────┬────────────────────────┤
│  Built-in      │  Skills (SKILL.md)     │
│  · Ripio API   │  ~/.finarg/skills/*/   │
│  · BCRA API    │  Created by agent      │
│  · Terminal    │  or bundled            │
│  · File + Vision                        │
│  · Web/Browser │                        │
│  · SIRADIG     │                        │
│  · Memory      │                        │
├────────────────┴────────────────────────┤
│  Persistence                             │
│  · SQLite (sessions)                     │
│  · MEMORY.md + USER.md (memory)          │
│  · afip_auth_state.json (SIRADIG session)│
└─────────────────────────────────────────┘
```

---

## Configuration

All data lives in `~/.finarg/`:

```
~/.finarg/
├── config.yaml              # Model, API settings
├── .env                     # API keys (never committed)
├── skills/                  # Skills (SKILL.md documents)
├── memories/                # Persistent memory
│   ├── MEMORY.md            # Agent notes
│   └── USER.md              # User profile
├── finarg.db                # SQLite (session history)
└── afip_auth_state.json     # SIRADIG login session (auto-generated)
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

# AFIP/ARCA (optional — enables SIRADIG + invoicing)
AFIP_CUIT=20XXXXXXXXX
AFIP_CLAVE_FISCAL=yourpassword
ARCA_CERT_PATH=/path/to/cert.crt
ARCA_KEY_PATH=/path/to/key.key
```

---

## Project context files

Create a `.finarg.md` file in any directory to give the agent project-specific context. The agent reads it automatically when you run `finarg` from that directory.

Also supports `AGENTS.md` and `CLAUDE.md`. Files are capped at 20,000 chars.

---

## Contributing

Contributions welcome! Fork the repo, create a branch, and open a PR.

```bash
git clone https://github.com/Gantalf/finarg.git
cd finarg
pip install -e ".[dev]"
python -m playwright install chromium
finarg version
```

### Ideas for contributions

- New API clients (MercadoPago, Binance, Bitso)
- New built-in tools
- Bundled skill packs (collections of SKILL.md for common workflows)
- New deduction categories for SIRADIG
- Bug fixes and documentation improvements

---

## Roadmap

- [ ] Trading (limit/market orders, swaps)
- [ ] Fiat on/off ramp (buy/sell crypto with ARS)
- [ ] Wire transfers and QR payments
- [ ] Scheduled/recurring payments
- [ ] Telegram and WhatsApp gateway
- [ ] MercadoPago integration
- [ ] Portfolio analytics and PnL tracking
- [ ] More SIRADIG deduction categories

---

## License

**MIT** — Free to use, modify, and distribute. See [LICENSE](LICENSE).

Built by [Gantalf](https://github.com/Gantalf).
