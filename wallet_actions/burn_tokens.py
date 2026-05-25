from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solana.rpc.types import TxOpts
from config import (
    DEFAULT_OWNER_WALLET,
    DEFAULT_TOKEN_DECIMALS,
    DEFAULT_TOKEN_MINT,
    RPC_URL,
    keypair_from_env,
)
from transaction_confirm import preview_or_confirm

print("🔥 Token Burn Script\n")

# ================== CONFIGURATION ==================
MINT_ADDRESS = DEFAULT_TOKEN_MINT
OWNER_WALLET = DEFAULT_OWNER_WALLET
# =====================================================

def main():
    client = Client(RPC_URL)

    payer = keypair_from_env("SOLANA_ACTIVE_PRIVATE_KEY_BASE58")
    print(f"✅ Burning from wallet: {payer.pubkey()}")

    # Get user input for burn amount (supports decimals)
    try:
        amount_str = input("\nHow many tokens do you want to burn? (e.g. 1.112233): ").strip()
        amount = float(amount_str)
        if amount <= 0:
            print("Amount must be greater than 0")
            return
    except ValueError:
        print("Invalid number!")
        return

    raw_amount = int(amount * (10 ** DEFAULT_TOKEN_DECIMALS))
    print(f"🔥 Burning {amount} tokens ({raw_amount} raw units)...")

    from spl.token.instructions import burn, BurnParams
    from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

    # Get Associated Token Account
    ata = Pubkey.find_program_address(
        [bytes(OWNER_WALLET), bytes(TOKEN_PROGRAM_ID), bytes(MINT_ADDRESS)],
        ASSOCIATED_TOKEN_PROGRAM_ID
    )[0]

    print(f"Using ATA: {ata}")

    try:
        # Burn instruction
        burn_ix = burn(BurnParams(
            program_id=TOKEN_PROGRAM_ID,
            account=ata,
            mint=MINT_ADDRESS,
            owner=payer.pubkey(),
            amount=raw_amount,
        ))

        recent_blockhash = client.get_latest_blockhash(Confirmed).value.blockhash

        message = MessageV0.try_compile(
            payer=payer.pubkey(),
            instructions=[burn_ix],
            address_lookup_table_accounts=[],
            recent_blockhash=recent_blockhash
        )

        tx = VersionedTransaction(message, [payer])
        if not preview_or_confirm(client, message, "burn transaction"):
            return
        result = client.send_raw_transaction(bytes(tx), opts=TxOpts(skip_preflight=True))

        print("\n✅ BURN TRANSACTION SENT SUCCESSFULLY!")
        print(f"Signature: {result.value}")
        print(f"🔗 https://explorer.solana.com/tx/{result.value}")

    except Exception as e:
        print(f"❌ Burn failed: {e}")

if __name__ == "__main__":
    main()