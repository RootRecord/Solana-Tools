from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solana.rpc.types import TxOpts
from config import (
    DEFAULT_NEW_AUTHORITY,
    DEFAULT_TOKEN_MINT,
    METADATA_PROGRAM_ID,
    RPC_URL,
    keypair_from_env,
)
import time
from transaction_confirm import preview_or_confirm

print("✅ Update Authority Transfer Script")

MINT = DEFAULT_TOKEN_MINT
NEW_AUTH = DEFAULT_NEW_AUTHORITY
METADATA_PID = METADATA_PROGRAM_ID

def main():
    client = Client(RPC_URL)

    payer = keypair_from_env("SOLANA_OLD_PRIVATE_KEY_BASE58")
    print(f"Using: {payer.pubkey()}")

    # Find Metadata PDA
    metadata_pda = Pubkey.find_program_address(
        [b"metadata", bytes(METADATA_PID), bytes(MINT)],
        METADATA_PID
    )[0]
    print(f"Metadata PDA: {metadata_pda}")

    from solders.instruction import Instruction, AccountMeta

    # Update Authority Instruction
    ix = Instruction(
        program_id=METADATA_PID,
        accounts=[
            AccountMeta(pubkey=metadata_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(pubkey=NEW_AUTH, is_signer=False, is_writable=False),
        ],
        data=bytes([11]) + bytes(NEW_AUTH)   # Update authority
    )

    try:
        blockhash = client.get_latest_blockhash(Confirmed).value.blockhash

        msg = MessageV0.try_compile(
            payer.pubkey(), [ix], [], blockhash
        )

        tx = VersionedTransaction(msg, [payer])
        if not preview_or_confirm(client, msg, "metadata authority transfer"):
            return
        result = client.send_raw_transaction(bytes(tx), opts=TxOpts(skip_preflight=True))

        print("\n🎉 UPDATE AUTHORITY TRANSACTION SENT!")
        print(f"Signature: {result.value}")
        print(f"🔗 https://explorer.solana.com/tx/{result.value}")
        print("\nWait 10-20 seconds and refresh Solscan.")

    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    main()