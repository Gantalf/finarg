"""Finarg tools package.

Importing this package triggers registration of all built-in tools.
"""

from finarg.tools import wallet, transfer, market_data, skill_creator

# Modules that use explicit registration functions
wallet.register_wallet_tools()
transfer.register_transfer_tools()
market_data.register_market_data_tools()

# skill_creator registers its tools at module level (no extra call needed)
