from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solana.rpc.types import TxOpts
from config import (
    METADATA_PROGRAM_ID,
    ROOTS_MINT_ADDRESS,
    ROOTS_NEW_AUTHORITY,
    RPC_URL,
    keypair_from_env,
)
import time

print("✅ Script started...")

# ================== CONFIGURATION ==================
MINT_ADDRESS = ROOTS_MINT_ADDRESS
NEW_AUTHORITY = ROOTS_NEW_AUTHORITY
# =====================================================

def main():
    print(f"🔄 Connecting to Helius RPC...")
    client = Client(RPC_URL)

    print("🔑 Loading wallet...")
    try:
        payer = keypair_from_env("SOLANA_OLD_PRIVATE_KEY_BASE58")
        print(f"✅ Wallet loaded: {payer.pubkey()}")
    except Exception as e:
        print(f"❌ Invalid private key: {e}")
        return

    print("🛠️ Building instructions...")

    instructions = []

    from spl.token.instructions import set_authority, SetAuthorityParams, AuthorityType
    from spl.token.constants import TOKEN_PROGRAM_ID

    # 1. Mint Authority
    instructions.append(set_authority(SetAuthorityParams(
        program_id=TOKEN_PROGRAM_ID,
        account=MINT_ADDRESS,
        authority=AuthorityType.MINT_TOKENS,
        current_authority=payer.pubkey(),
        new_authority=NEW_AUTHORITY,
    )))

    # 2. Freeze Authority
    instructions.append(set_authority(SetAuthorityParams(
        program_id=TOKEN_PROGRAM_ID,
        account=MINT_ADDRESS,
        authority=AuthorityType.FREEZE_ACCOUNT,
        current_authority=payer.pubkey(),
        new_authority=NEW_AUTHORITY,
    )))

    # 3. Update Authority (Metadata) - Improved version
    metadata_seeds = [b"metadata", bytes(METADATA_PROGRAM_ID), bytes(MINT_ADDRESS)]
    metadata_pda = Pubkey.find_program_address(metadata_seeds, METADATA_PROGRAM_ID)[0]

    from solders.instruction import Instruction, AccountMeta

    # Better discriminator + data for Update Authority
    update_data = bytes([11]) + bytes(NEW_AUTHORITY)   # 11 = UpdateMetadataAccountV2

    update_auth_ix = Instruction(
        program_id=METADATA_PROGRAM_ID,
        accounts=[
            AccountMeta(pubkey=metadata_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(pubkey=NEW_AUTHORITY, is_signer=False, is_writable=False),
        ],
        data=update_data
    )
    instructions.append(update_auth_ix)

    print(f"📦 Total instructions: {len(instructions)}")
    print("🚀 Sending transaction...")

    for attempt in range(6):
        try:
            recent_blockhash = client.get_latest_blockhash(Confirmed).value.blockhash

            message = MessageV0.try_compile(
                payer=payer.pubkey(),
                instructions=instructions,
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash
            )

            tx = VersionedTransaction(message, [payer])
            opts = TxOpts(skip_preflight=True, max_retries=3)

            result = client.send_raw_transaction(bytes(tx), opts=opts)

            print("\n🎉 TRANSACTION SENT SUCCESSFULLY!")
            print(f"Signature: {result.value}")
            print(f"🔗 https://explorer.solana.com/tx/{result.value}")
            print("\nWait 10-20 seconds and refresh solscan.io to check if Update Authority changed.")
            return

        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            if attempt < 5:
                time.sleep(3)

    print("\n❌ All attempts failed.")

if __name__ == "__main__":
    main()