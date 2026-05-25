import os
from pathlib import Path

import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey


def _load_dotenv() -> None:
    """Load .env from this project without requiring python-dotenv."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]

    for env_path in candidates:
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv()


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def env_int(name: str, default: int) -> int:
    value = env(name, str(default))
    return int(value)


def env_float(name: str, default: float) -> float:
    value = env(name, str(default))
    return float(value)


def env_list(name: str, default: str = "") -> list[str]:
    value = env(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def pubkey_from_env(name: str, default: str | None = None, *, required: bool = False) -> Pubkey:
    value = env(name, default, required=required)
    return Pubkey.from_string(value)


def keypair_from_env(name: str) -> Keypair:
    value = env(name, required=True)
    return Keypair.from_bytes(base58.b58decode(value))


RPC_URL = env("SOLANA_RPC_URL", required=True)

SPL_TOKEN_PROGRAM_ID = pubkey_from_env(
    "SPL_TOKEN_PROGRAM_ID",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
)
TOKEN_2022_PROGRAM_ID = pubkey_from_env(
    "TOKEN_2022_PROGRAM_ID",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
)
ASSOCIATED_TOKEN_PROGRAM_ID = pubkey_from_env(
    "ASSOCIATED_TOKEN_PROGRAM_ID",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
)
METADATA_PROGRAM_ID = pubkey_from_env(
    "METADATA_PROGRAM_ID",
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s",
)

SOL_MINT = pubkey_from_env("SOL_MINT", "So11111111111111111111111111111111111111112")
USDC_MINT = pubkey_from_env("USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")

DEFAULT_TOKEN_MINT = pubkey_from_env("DEFAULT_TOKEN_MINT", required=True)
DEFAULT_OWNER_WALLET = pubkey_from_env("DEFAULT_OWNER_WALLET", required=True)
DEFAULT_DESTINATION_WALLET = pubkey_from_env("DEFAULT_DESTINATION_WALLET", str(DEFAULT_OWNER_WALLET))
DEFAULT_NEW_AUTHORITY = pubkey_from_env("DEFAULT_NEW_AUTHORITY", str(DEFAULT_OWNER_WALLET))

DEFAULT_TOKENS_TO_MINT = env_int("DEFAULT_TOKENS_TO_MINT", 100)
DEFAULT_TOKEN_DECIMALS = env_int("DEFAULT_TOKEN_DECIMALS", 9)
DEFAULT_THAW_ACCOUNTS = env_list("DEFAULT_THAW_ACCOUNTS")

TRADING_HISTORY_FILE = env("TRADING_HISTORY_FILE", "trading_history.json")
SOL_PRICE_FALLBACK = env_float("SOL_PRICE_FALLBACK", 87.5)
JUPITER_QUOTE_URL = env("JUPITER_QUOTE_URL", "https://quote-api.jup.ag/v6/quote")
JUPITER_SWAP_URL = env("JUPITER_SWAP_URL", "https://quote-api.jup.ag/v6/swap")
COINGECKO_SOL_PRICE_URL = env(
    "COINGECKO_SOL_PRICE_URL",
    "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
)
