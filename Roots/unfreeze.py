from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solana.rpc.types import TxOpts
from config import ROOTS_MINT_ADDRESS, ROOTS_UNFREEZE_ACCOUNTS, RPC_URL, keypair_from_env

print("🔍 LP Unfreeze Diagnostic + Attempt\n")

MINT = ROOTS_MINT_ADDRESS
ACCOUNTS = ROOTS_UNFREEZE_ACCOUNTS

client = Client(RPC_URL)
payer = keypair_from_env("SOLANA_ACTIVE_PRIVATE_KEY_BASE58")

print(f"Using Freeze Authority: {payer.pubkey()}")

from spl.token.instructions import thaw_account, ThawAccountParams
from spl.token.constants import TOKEN_PROGRAM_ID

instructions = []

for addr_str in ACCOUNTS:
    acc = Pubkey.from_string(addr_str)
    print(f"\nChecking {acc}...")

    try:
        info = client.get_account_info(acc).value
        if info:
            print(f"  Owner Program: {info.owner}")
            if info.owner == TOKEN_PROGRAM_ID:
                print("  → Is a Token Account")
                ix = thaw_account(ThawAccountParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=acc,
                    mint=MINT,
                    authority=payer.pubkey(),
                ))
                instructions.append(ix)
                print("  → Unfreeze instruction added")
            else:
                print("  → Not a standard Token Account (likely LP position)")
        else:
            print("  → Account does not exist")
    except Exception as e:
        print(f"  Error checking: {e}")

if instructions:
    print(f"\n🚀 Sending unfreeze for {len(instructions)} accounts...")
    try:
        recent = client.get_latest_blockhash(Confirmed).value.blockhash
        msg = MessageV0.try_compile(payer.pubkey(), instructions, [], recent)
        tx = VersionedTransaction(msg, [payer])
        result = client.send_raw_transaction(bytes(tx), opts=TxOpts(skip_preflight=True))
        print(f"\n✅ Transaction sent: {result.value}")
        print(f"https://explorer.solana.com/tx/{result.value}")
    except Exception as e:
        print(f"❌ Failed: {e}")
else:
    print("\nNo unfreeze instructions were created.")
