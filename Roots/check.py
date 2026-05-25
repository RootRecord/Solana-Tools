from solders.pubkey import Pubkey
from solana.rpc.api import Client
from config import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    ROOTS_MINT_ADDRESS,
    ROOTS_OWNER_WALLET,
    RPC_URL,
    SPL_TOKEN_PROGRAM_ID,
)

print("✅ Balance Checker")

MINT = ROOTS_MINT_ADDRESS
WALLET = ROOTS_OWNER_WALLET

client = Client(RPC_URL)

# Get ATA
ata = Pubkey.find_program_address(
    [bytes(WALLET), bytes(SPL_TOKEN_PROGRAM_ID), bytes(MINT)],
    ASSOCIATED_TOKEN_PROGRAM_ID,
)[0]

print(f"Your ATA: {ata}")

try:
    balance = client.get_token_account_balance(ata)
    print(f"Current balance: {balance.value.ui_amount} tokens")
    print(f"Raw balance: {balance.value.amount}")
except:
    print("No ATA found or zero balance")