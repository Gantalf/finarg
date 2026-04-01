# Finarg

AI-powered financial agent for Argentina/LATAM.

```
pip install finarg
finarg init
finarg
```

## Features

- Crypto wallet management (balances, deposits, withdrawals) via Ripio
- Argentine dollar rates (oficial, blue, MEP) via BCRA
- Self-extending: the agent creates its own new tools on demand
- Beautiful Bloomberg-inspired terminal UI

## Quick Start

```bash
pip install finarg
finarg init        # Setup wizard (API keys)
finarg             # Launch terminal UI
finarg chat        # Simple chat mode
```

## Architecture

```
User (Terminal TUI)
       |
   FinargAgent (LLM -> tool calls -> execute -> repeat)
       |
   ToolRegistry (built-in tools + user skills)
       |                    |
   API Clients          Skills (~/.finarg/skills/*.py)
   (Ripio, BCRA)        Auto-created by the agent
       |
   SQLite (sessions, transaction log)
```

## License

AGPL-3.0 — Free to use and modify, but any derivative work must also be open source.
