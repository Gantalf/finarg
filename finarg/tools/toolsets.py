"""Toolset definitions for Finarg.

Each toolset groups related tools so the agent configuration can enable or
disable entire categories at once. Follows Hermes toolsets.py pattern.
"""

from __future__ import annotations

TOOLSETS: dict[str, dict[str, object]] = {
    "wallet": {
        "description": "Crypto wallet management",
        "tools": ["get_balances", "get_deposit_address"],
    },
    "transfer": {
        "description": "Crypto transfers and withdrawals",
        "tools": ["withdraw_crypto"],
    },
    "market_data": {
        "description": "Market data and exchange rates",
        "tools": ["get_ticker", "get_dolar_rates"],
    },
    "web": {
        "description": "Web search and webpage reading",
        "tools": ["web_search", "read_webpage"],
    },
    "browser": {
        "description": "Headless browser (navigate, click, type, scroll)",
        "tools": [
            "browser_navigate", "browser_snapshot", "browser_click",
            "browser_type", "browser_scroll", "browser_back", "browser_close",
        ],
    },
    "terminal": {
        "description": "Execute shell commands",
        "tools": ["terminal"],
    },
    "file": {
        "description": "File operations (read, write, patch, search)",
        "tools": ["read_file", "write_file", "patch", "search_files"],
    },
    "skills": {
        "description": "Skill management and discovery",
        "tools": ["skills_list", "skill_view", "skill_manage"],
    },
    "memory": {
        "description": "Persistent memory across sessions",
        "tools": ["memory"],
    },
}
