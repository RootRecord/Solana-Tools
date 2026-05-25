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

print("✅ Authority Transfer Script Started...")

MINT = DEFAULT_TOKEN_MINT
NEW = DEFAULT_NEW_AUTHORITY
METADATA_PID = METADATA_PROGRAM_ID

def main():
    client = Client(RPC_URL)

    payer = keypair_from_env("SOLANA_OLD_PRIVATE_KEY_BASE58")
    print(f"Using wallet: {payer.pubkey()}")

    instructions = []

    from spl.token.instructions import set_authority, SetAuthorityParams, AuthorityType
    from spl.token.constants import TOKEN_PROGRAM_ID

    # Mint Authority
    instructions.append(set_authority(SetAuthorityParams(
        program_id=TOKEN_PROGRAM_ID,
        account=MINT,
        authority=AuthorityType.MINT_TOKENS,
        current_authority=payer.pubkey(),
        new_authority=NEW,
    )))

    # Freeze Authority
    instructions.append(set_authority(SetAuthorityParams(
        program_id=TOKEN_PROGRAM_ID,
        account=MINT,
        authority=AuthorityType.FREEZE_ACCOUNT,
        current_authority=payer.pubkey(),
        new_authority=NEW,
    )))

    # Update Authority
    metadata_pda = Pubkey.find_program_address(
        [b"metadata", bytes(METADATA_PID), bytes(MINT)],
        METADATA_PID
    )[0]

    from solders.instruction import Instruction, AccountMeta
    update_ix = Instruction(
        program_id=METADATA_PID,
        accounts=[
            AccountMeta(pubkey=metadata_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(pubkey=NEW, is_signer=False, is_writable=False),
        ],
        data=bytes([11]) + bytes(NEW)
    )
    instructions.append(update_ix)

    print("🚀 Sending full authority transfer...")

    for attempt in range(5):
        try:
            blockhash = client.get_latest_blockhash(Confirmed).value.blockhash
            msg = MessageV0.try_compile(payer.pubkey(), instructions, [], blockhash)
            tx = VersionedTransaction(msg, [payer])

            if not preview_or_confirm(client, msg, "full authority transfer"):
                return
            result = client.send_raw_transaction(bytes(tx), opts=TxOpts(skip_preflight=True))

            print("\n🎉 AUTHORITY TRANSFER SENT!")
            print(f"Signature: {result.value}")
            print(f"🔗 https://explorer.solana.com/tx/{result.value}")
            print("\nWait 15 seconds then check solscan.io/token/... again.")
            return
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()