from __future__ import annotations

import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "y", "on"}


def preview_or_confirm(client, message, label: str = "transaction") -> bool:
    fee_lamports = 0
    try:
        fee_lamports = int(client.get_fee_for_message(message).value or 0)
    except Exception as exc:
        print(f"Estimated network fee: unavailable ({exc})")
    else:
        print(f"Estimated network fee: {fee_lamports} lamports ({fee_lamports / 1_000_000_000:.9f} SOL)")
        print("Estimate excludes token amounts, rent deposits, DEX/platform fees, and later priority-fee changes unless shown separately.")

    if not env_bool("SEND_TRANSACTION", False):
        print(f"DRY RUN: {label} was built, but no transaction was broadcast.")
        return False

    if env_bool("SOLANA_TOOLS_USER_CONFIRMED", False):
        print("Dashboard confirmation received. Proceeding with broadcast.")
        return True

    answer = input("Type EXECUTE to confirm this transaction: ").strip()
    if answer != "EXECUTE":
        print("Transaction cancelled before broadcast.")
        return False
    return True
