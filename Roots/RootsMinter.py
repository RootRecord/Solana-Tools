from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solana.rpc.types import TxOpts
from config import (
    ROOTS_DESTINATION_WALLET,
    ROOTS_MINT_ADDRESS,
    ROOTS_TOKEN_DECIMALS,
    ROOTS_TOKENS_TO_MINT,
    RPC_URL,
    keypair_from_env,
)
from transaction_confirm import preview_or_confirm

print("✅ All-In-One Mint Script with Authority Check")

# ================== CONFIGURATION ==================
MINT_ADDRESS = ROOTS_MINT_ADDRESS
DESTINATION_WALLET = ROOTS_DESTINATION_WALLET
TOKENS_TO_MINT = ROOTS_TOKENS_TO_MINT
# =====================================================

def main():
    client = Client(RPC_URL)
    payer = keypair_from_env("SOLANA_ACTIVE_PRIVATE_KEY_BASE58")
    print(f"✅ Wallet: {payer.pubkey()}")

    # === CHECK CURRENT MINT AUTHORITY ===
    print("🔍 Checking Mint Authority...")
    mint_info = client.get_account_info(MINT_ADDRESS).value
    if mint_info and mint_info.data:
        # Simple check - first 32 bytes after header is mint authority
        authority_bytes = mint_info.data[4:36]
        current_authority = Pubkey(authority_bytes)
        print(f"Current Mint Authority on-chain: {current_authority}")

        if current_authority != payer.pubkey():
            print("❌ WARNING: Your wallet is NOT the current Mint Authority!")
            print("   You must transfer Mint Authority first from the old wallet.")
            return

    raw_amount = int(TOKENS_TO_MINT * (10 ** ROOTS_TOKEN_DECIMALS))

    from spl.token.instructions import mint_to, MintToParams, create_associated_token_account
    from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

    ata = Pubkey.find_program_address(
        [bytes(DESTINATION_WALLET), bytes(TOKEN_PROGRAM_ID), bytes(MINT_ADDRESS)],
        ASSOCIATED_TOKEN_PROGRAM_ID
    )[0]

    print(f"Target ATA: {ata}")

    instructions = []

    # Create ATA (safe)
    instructions.append(create_associated_token_account(
        payer=payer.pubkey(),
        owner=DESTINATION_WALLET,
        mint=MINT_ADDRESS
    ))

    # Mint
    instructions.append(mint_to(MintToParams(
        program_id=TOKEN_PROGRAM_ID,
        mint=MINT_ADDRESS,
        dest=ata,
        mint_authority=payer.pubkey(),
        amount=raw_amount,
    )))

    print(f"🪙 Minting {TOKENS_TO_MINT:,} tokens...")

    try:
        recent_blockhash = client.get_latest_blockhash(Confirmed).value.blockhash

        message = MessageV0.try_compile(
            payer=payer.pubkey(),
            instructions=instructions,
            address_lookup_table_accounts=[],
            recent_blockhash=recent_blockhash
        )

        tx = VersionedTransaction(message, [payer])
        if not preview_or_confirm(client, message, "mint transaction"):
            return
        result = client.send_raw_transaction(bytes(tx), opts=TxOpts(skip_preflight=True))

        print("\n🎉 TRANSACTION SENT!")
        print(f"Signature: {result.value}")
        print(f"🔗 https://explorer.solana.com/tx/{result.value}")
        print("\nCheck supply on Solscan in 15 seconds.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()