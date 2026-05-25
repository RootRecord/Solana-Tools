from __future__ import annotations

from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "isolated_scripts"


COMMON = r'''
import json
import os
from pathlib import Path

import base58
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey


def load_dotenv() -> None:
    search_roots = [Path.cwd(), *Path(__file__).resolve().parents]
    for env_path in [root / ".env" for root in search_roots]:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def env_int(name: str, default: int = 0) -> int:
    return int(env(name, str(default)))


def env_float(name: str, default: float = 0.0) -> float:
    return float(env(name, str(default)))


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "y", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    value = env(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def pubkey(name: str, default: str | None = None, *, required: bool = True) -> Pubkey:
    return Pubkey.from_string(env(name, default, required=required))


def keypair(name: str = "SOLANA_ACTIVE_PRIVATE_KEY_BASE58") -> Keypair:
    return Keypair.from_bytes(base58.b58decode(env(name, required=True)))


def client() -> Client:
    return Client(env("SOLANA_RPC_URL", "https://api.devnet.solana.com"))


def print_response(resp) -> None:
    if hasattr(resp, "to_json"):
        print(resp.to_json())
        return
    try:
        print(json.dumps(resp, indent=2, default=str))
    except TypeError:
        print(resp)


def send_or_print(instructions, signer_env: str = "SOLANA_ACTIVE_PRIVATE_KEY_BASE58") -> None:
    if not env_bool("SEND_TRANSACTION", False):
        print("DRY RUN: set SEND_TRANSACTION=true to broadcast.")
        for index, instruction in enumerate(instructions, start=1):
            print(f"Instruction {index}: {instruction}")
        return

    from solana.rpc.types import TxOpts
    from solders.message import MessageV0
    from solders.transaction import VersionedTransaction

    payer = keypair(signer_env)
    rpc = client()
    blockhash = rpc.get_latest_blockhash().value.blockhash
    msg = MessageV0.try_compile(
        payer=payer.pubkey(),
        instructions=instructions,
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )
    tx = VersionedTransaction(msg, [payer])
    print_response(rpc.send_raw_transaction(bytes(tx), opts=TxOpts(skip_preflight=False)))
'''


def script(category: str, name: str, title: str, body: str) -> dict[str, str]:
    return {"category": category, "name": name, "title": title, "body": dedent(body).strip()}


SCRIPTS = [
    # RPC: health, account, cluster, block, tx, staking, token reads.
    script("rpc", "is_connected", "Check RPC health", 'print(client().is_connected())'),
    script("rpc", "get_balance", "Get SOL balance", 'print_response(client().get_balance(pubkey("TARGET_PUBKEY")))'),
    script("rpc", "get_account_info", "Get raw account info", 'print_response(client().get_account_info(pubkey("TARGET_PUBKEY")))'),
    script("rpc", "get_account_info_json_parsed", "Get parsed account info", 'print_response(client().get_account_info_json_parsed(pubkey("TARGET_PUBKEY")))'),
    script("rpc", "get_multiple_accounts", "Get multiple accounts", '''
keys = [Pubkey.from_string(value) for value in env_list("TARGET_PUBKEYS")]
print_response(client().get_multiple_accounts(keys))
'''),
    script("rpc", "get_multiple_accounts_json_parsed", "Get multiple parsed accounts", '''
keys = [Pubkey.from_string(value) for value in env_list("TARGET_PUBKEYS")]
print_response(client().get_multiple_accounts_json_parsed(keys))
'''),
    script("rpc", "get_program_accounts", "Get program accounts", '''
from solana.rpc.types import MemcmpOpts

filters = []
if env("FILTER_DATA_SIZE"):
    filters.append(int(env("FILTER_DATA_SIZE")))
if env("FILTER_MEMCMP_OFFSET") and env("FILTER_MEMCMP_BYTES"):
    filters.append(MemcmpOpts(offset=env_int("FILTER_MEMCMP_OFFSET"), bytes=env("FILTER_MEMCMP_BYTES")))
print_response(client().get_program_accounts(pubkey("PROGRAM_ID"), filters=filters or None))
'''),
    script("rpc", "get_program_accounts_json_parsed", "Get parsed program accounts", 'print_response(client().get_program_accounts_json_parsed(pubkey("PROGRAM_ID")))'),
    script("rpc", "get_block", "Get block by slot", 'print_response(client().get_block(env_int("SLOT"), max_supported_transaction_version=env_int("MAX_SUPPORTED_TRANSACTION_VERSION", 0)))'),
    script("rpc", "get_block_commitment", "Get block commitment", 'print_response(client().get_block_commitment(env_int("SLOT")))'),
    script("rpc", "get_block_height", "Get current block height", 'print_response(client().get_block_height())'),
    script("rpc", "get_block_time", "Get block time", 'print_response(client().get_block_time(env_int("SLOT")))'),
    script("rpc", "get_blocks", "Get block slots", 'print_response(client().get_blocks(env_int("START_SLOT"), env_int("END_SLOT") or None))'),
    script("rpc", "get_first_available_block", "Get first available block", 'print_response(client().get_first_available_block())'),
    script("rpc", "get_slot", "Get current slot", 'print_response(client().get_slot())'),
    script("rpc", "get_slot_leader", "Get slot leader", 'print_response(client().get_slot_leader())'),
    script("rpc", "get_slot_leaders", "Get slot leaders", 'print_response(client().get_slot_leaders(env_int("START_SLOT"), env_int("LIMIT", 10)))'),
    script("rpc", "get_cluster_nodes", "Get cluster nodes", 'print_response(client().get_cluster_nodes())'),
    script("rpc", "get_epoch_info", "Get epoch info", 'print_response(client().get_epoch_info())'),
    script("rpc", "get_epoch_schedule", "Get epoch schedule", 'print_response(client().get_epoch_schedule())'),
    script("rpc", "get_genesis_hash", "Get genesis hash", 'print_response(client().get_genesis_hash())'),
    script("rpc", "get_identity", "Get RPC node identity", 'print_response(client().get_identity())'),
    script("rpc", "get_version", "Get RPC node version", 'print_response(client().get_version())'),
    script("rpc", "get_recent_performance_samples", "Get performance samples", 'print_response(client().get_recent_performance_samples(env_int("LIMIT", 10)))'),
    script("rpc", "get_supply", "Get SOL supply", 'print_response(client().get_supply())'),
    script("rpc", "get_transaction_count", "Get transaction count", 'print_response(client().get_transaction_count())'),
    script("rpc", "get_minimum_balance_for_rent_exemption", "Get rent exemption amount", 'print_response(client().get_minimum_balance_for_rent_exemption(env_int("ACCOUNT_DATA_LENGTH")))'),
    script("rpc", "get_largest_accounts", "Get largest SOL accounts", 'print_response(client().get_largest_accounts())'),
    script("rpc", "get_inflation_governor", "Get inflation governor", 'print_response(client().get_inflation_governor())'),
    script("rpc", "get_inflation_rate", "Get inflation rate", 'print_response(client().get_inflation_rate())'),
    script("rpc", "get_inflation_reward", "Get inflation reward", '''
keys = [Pubkey.from_string(value) for value in env_list("TARGET_PUBKEYS")]
print_response(client().get_inflation_reward(keys, epoch=env_int("EPOCH") or None))
'''),
    script("rpc", "get_vote_accounts", "Get vote accounts", 'print_response(client().get_vote_accounts())'),
    script("rpc", "get_latest_blockhash", "Get latest blockhash", 'print_response(client().get_latest_blockhash())'),
    script("rpc", "get_fee_for_message", "Get fee for a simple message", '''
from solders.message import MessageV0
from solders.system_program import TransferParams, transfer

payer = keypair()
ix = transfer(TransferParams(from_pubkey=payer.pubkey(), to_pubkey=pubkey("RECIPIENT_PUBKEY"), lamports=env_int("LAMPORTS", 1)))
blockhash = client().get_latest_blockhash().value.blockhash
message = MessageV0.try_compile(payer.pubkey(), [ix], [], blockhash)
print_response(client().get_fee_for_message(message))
'''),
    script("rpc", "get_signature_statuses", "Get signature statuses", '''
from solders.signature import Signature

signatures = [Signature.from_string(value) for value in env_list("SIGNATURES")]
print_response(client().get_signature_statuses(signatures, search_transaction_history=env_bool("SEARCH_TRANSACTION_HISTORY")))
'''),
    script("rpc", "get_signatures_for_address", "Get signatures for address", 'print_response(client().get_signatures_for_address(pubkey("TARGET_PUBKEY"), limit=env_int("LIMIT", 20)))'),
    script("rpc", "get_transaction", "Get transaction details", '''
from solders.signature import Signature

print_response(client().get_transaction(
    Signature.from_string(env("SIGNATURE", required=True)),
    encoding=env("ENCODING", "json"),
    max_supported_transaction_version=env_int("MAX_SUPPORTED_TRANSACTION_VERSION", 0),
))
'''),
    script("rpc", "get_token_account_balance", "Get token account balance", 'print_response(client().get_token_account_balance(pubkey("TOKEN_ACCOUNT")))'),
    script("rpc", "get_token_accounts_by_owner", "Get token accounts by owner", '''
from solana.rpc.types import TokenAccountOpts

opts = TokenAccountOpts(mint=pubkey("MINT_ADDRESS")) if env("MINT_ADDRESS") else TokenAccountOpts(program_id=pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")))
print_response(client().get_token_accounts_by_owner(pubkey("OWNER_PUBKEY"), opts))
'''),
    script("rpc", "get_token_accounts_by_owner_json_parsed", "Get parsed token accounts by owner", '''
from solana.rpc.types import TokenAccountOpts

opts = TokenAccountOpts(mint=pubkey("MINT_ADDRESS")) if env("MINT_ADDRESS") else TokenAccountOpts(program_id=pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")))
print_response(client().get_token_accounts_by_owner_json_parsed(pubkey("OWNER_PUBKEY"), opts))
'''),
    script("rpc", "get_token_accounts_by_delegate", "Get token accounts by delegate", '''
from solana.rpc.types import TokenAccountOpts

opts = TokenAccountOpts(mint=pubkey("MINT_ADDRESS")) if env("MINT_ADDRESS") else TokenAccountOpts(program_id=pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")))
print_response(client().get_token_accounts_by_delegate(pubkey("DELEGATE_PUBKEY"), opts))
'''),
    script("rpc", "get_token_accounts_by_delegate_json_parsed", "Get parsed token accounts by delegate", '''
from solana.rpc.types import TokenAccountOpts

opts = TokenAccountOpts(mint=pubkey("MINT_ADDRESS")) if env("MINT_ADDRESS") else TokenAccountOpts(program_id=pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")))
print_response(client().get_token_accounts_by_delegate_json_parsed(pubkey("DELEGATE_PUBKEY"), opts))
'''),
    script("rpc", "get_token_largest_accounts", "Get largest token accounts", 'print_response(client().get_token_largest_accounts(pubkey("MINT_ADDRESS")))'),
    script("rpc", "get_token_supply", "Get token supply", 'print_response(client().get_token_supply(pubkey("MINT_ADDRESS")))'),
    script("rpc", "request_airdrop", "Request devnet/testnet airdrop", '''
print_response(client().request_airdrop(pubkey("RECIPIENT_PUBKEY"), env_int("LAMPORTS", 1_000_000_000)))
'''),
    script("rpc", "simulate_sol_transfer", "Simulate a SOL transfer", '''
from solders.message import MessageV0
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction

payer = keypair()
ix = transfer(TransferParams(from_pubkey=payer.pubkey(), to_pubkey=pubkey("RECIPIENT_PUBKEY"), lamports=env_int("LAMPORTS", 1)))
blockhash = client().get_latest_blockhash().value.blockhash
msg = MessageV0.try_compile(payer.pubkey(), [ix], [], blockhash)
tx = VersionedTransaction(msg, [payer])
print_response(client().simulate_transaction(tx))
'''),

    # solders utility scripts.
    script("solders", "generate_keypair", "Generate a new keypair", '''
kp = Keypair()
print(f"PUBLIC_KEY={kp.pubkey()}")
print(f"NEW_KEYPAIR_SECRET_BASE58={base58.b58encode(bytes(kp)).decode()}")
'''),
    script("solders", "parse_pubkey", "Parse and print a pubkey", 'print(pubkey("TARGET_PUBKEY"))'),
    script("solders", "parse_signature", "Parse and print a signature", '''
from solders.signature import Signature

print(Signature.from_string(env("SIGNATURE", required=True)))
'''),
    script("solders", "derive_pda", "Derive PDA from string seeds", '''
seeds = [item.encode("utf-8") for item in env_list("PDA_SEEDS")]
address, bump = Pubkey.find_program_address(seeds, pubkey("PROGRAM_ID"))
print(f"PDA={address}")
print(f"BUMP={bump}")
'''),
    script("solders", "create_with_seed", "Create seeded address", '''
address = Pubkey.create_with_seed(pubkey("BASE_PUBKEY"), env("SEED", required=True), pubkey("PROGRAM_ID"))
print(address)
'''),
    script("solders", "sign_message", "Sign arbitrary message", '''
signature = keypair().sign_message(env("MESSAGE", required=True).encode("utf-8"))
print(signature)
'''),
    script("solders", "build_raw_instruction", "Build a raw instruction preview", '''
from solders.instruction import AccountMeta, Instruction

accounts = [
    AccountMeta(pubkey=Pubkey.from_string(item), is_signer=False, is_writable=False)
    for item in env_list("ACCOUNT_PUBKEYS")
]
data = bytes.fromhex(env("INSTRUCTION_DATA_HEX", ""))
ix = Instruction(pubkey("PROGRAM_ID"), data, accounts)
print(ix)
'''),
    script("solders", "versioned_transaction_from_base64", "Parse versioned transaction bytes", '''
import base64
from solders.transaction import VersionedTransaction

tx = VersionedTransaction.from_bytes(base64.b64decode(env("TRANSACTION_BASE64", required=True)))
print(tx)
'''),

    # System Program write scripts.
    script("system", "transfer_sol", "Transfer SOL", '''
from solders.system_program import TransferParams, transfer

payer = keypair()
ix = transfer(TransferParams(from_pubkey=payer.pubkey(), to_pubkey=pubkey("RECIPIENT_PUBKEY"), lamports=env_int("LAMPORTS")))
send_or_print([ix])
'''),
    script("system", "create_account", "Create system account", '''
from solders.system_program import CreateAccountParams, create_account

payer = keypair()
new_account = keypair("NEW_ACCOUNT_PRIVATE_KEY_BASE58")
ix = create_account(CreateAccountParams(
    from_pubkey=payer.pubkey(),
    to_pubkey=new_account.pubkey(),
    lamports=env_int("LAMPORTS"),
    space=env_int("SPACE"),
    owner=pubkey("OWNER_PROGRAM_ID"),
))
send_or_print([ix])
'''),
    script("system", "allocate", "Allocate account space", '''
from solders.system_program import AllocateParams, allocate

target = keypair("TARGET_ACCOUNT_PRIVATE_KEY_BASE58")
ix = allocate(AllocateParams(pubkey=target.pubkey(), space=env_int("SPACE")))
send_or_print([ix], signer_env="TARGET_ACCOUNT_PRIVATE_KEY_BASE58")
'''),
    script("system", "assign", "Assign account owner", '''
from solders.system_program import AssignParams, assign

target = keypair("TARGET_ACCOUNT_PRIVATE_KEY_BASE58")
ix = assign(AssignParams(pubkey=target.pubkey(), owner=pubkey("OWNER_PROGRAM_ID")))
send_or_print([ix], signer_env="TARGET_ACCOUNT_PRIVATE_KEY_BASE58")
'''),
    script("system", "transfer_with_seed", "Transfer SOL from seeded account", '''
from solders.system_program import TransferWithSeedParams, transfer_with_seed

base = keypair("BASE_PRIVATE_KEY_BASE58")
ix = transfer_with_seed(TransferWithSeedParams(
    from_pubkey=pubkey("FROM_PUBKEY"),
    from_base=base.pubkey(),
    from_seed=env("FROM_SEED", required=True),
    from_owner=pubkey("FROM_OWNER_PROGRAM_ID"),
    to_pubkey=pubkey("RECIPIENT_PUBKEY"),
    lamports=env_int("LAMPORTS"),
))
send_or_print([ix], signer_env="BASE_PRIVATE_KEY_BASE58")
'''),

    # SPL Token scripts.
    script("spl_token", "derive_ata", "Derive associated token account", '''
program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
ata_program = pubkey("ASSOCIATED_TOKEN_PROGRAM_ID", env("ASSOCIATED_TOKEN_PROGRAM_ID", "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"))
ata = Pubkey.find_program_address([bytes(pubkey("OWNER_PUBKEY")), bytes(program_id), bytes(pubkey("MINT_ADDRESS"))], ata_program)[0]
print(ata)
'''),
    script("spl_token", "create_associated_token_account", "Create associated token account", '''
from spl.token.instructions import create_associated_token_account

payer = keypair()
ix = create_associated_token_account(payer=payer.pubkey(), owner=pubkey("OWNER_PUBKEY"), mint=pubkey("MINT_ADDRESS"))
send_or_print([ix])
'''),
    script("spl_token", "mint_to", "Mint tokens", '''
from spl.token.instructions import MintToParams, mint_to

program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
authority = keypair("MINT_AUTHORITY_PRIVATE_KEY_BASE58")
ix = mint_to(MintToParams(program_id=program_id, mint=pubkey("MINT_ADDRESS"), dest=pubkey("DESTINATION_TOKEN_ACCOUNT"), mint_authority=authority.pubkey(), amount=env_int("RAW_AMOUNT")))
send_or_print([ix], signer_env="MINT_AUTHORITY_PRIVATE_KEY_BASE58")
'''),
    script("spl_token", "burn", "Burn tokens", '''
from spl.token.instructions import BurnParams, burn

program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
owner = keypair("TOKEN_OWNER_PRIVATE_KEY_BASE58")
ix = burn(BurnParams(program_id=program_id, account=pubkey("TOKEN_ACCOUNT"), mint=pubkey("MINT_ADDRESS"), owner=owner.pubkey(), amount=env_int("RAW_AMOUNT")))
send_or_print([ix], signer_env="TOKEN_OWNER_PRIVATE_KEY_BASE58")
'''),
    script("spl_token", "transfer_checked", "Transfer checked tokens", '''
from spl.token.instructions import TransferCheckedParams, transfer_checked

program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
owner = keypair("TOKEN_OWNER_PRIVATE_KEY_BASE58")
ix = transfer_checked(TransferCheckedParams(program_id=program_id, source=pubkey("SOURCE_TOKEN_ACCOUNT"), mint=pubkey("MINT_ADDRESS"), dest=pubkey("DESTINATION_TOKEN_ACCOUNT"), owner=owner.pubkey(), amount=env_int("RAW_AMOUNT"), decimals=env_int("DECIMALS", 9)))
send_or_print([ix], signer_env="TOKEN_OWNER_PRIVATE_KEY_BASE58")
'''),
    script("spl_token", "approve", "Approve token delegate", '''
from spl.token.instructions import ApproveParams, approve

program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
owner = keypair("TOKEN_OWNER_PRIVATE_KEY_BASE58")
ix = approve(ApproveParams(program_id=program_id, source=pubkey("TOKEN_ACCOUNT"), delegate=pubkey("DELEGATE_PUBKEY"), owner=owner.pubkey(), amount=env_int("RAW_AMOUNT")))
send_or_print([ix], signer_env="TOKEN_OWNER_PRIVATE_KEY_BASE58")
'''),
    script("spl_token", "revoke", "Revoke token delegate", '''
from spl.token.instructions import RevokeParams, revoke

program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
owner = keypair("TOKEN_OWNER_PRIVATE_KEY_BASE58")
ix = revoke(RevokeParams(program_id=program_id, account=pubkey("TOKEN_ACCOUNT"), owner=owner.pubkey()))
send_or_print([ix], signer_env="TOKEN_OWNER_PRIVATE_KEY_BASE58")
'''),
    script("spl_token", "freeze_account", "Freeze token account", '''
from spl.token.instructions import FreezeAccountParams, freeze_account

program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
authority = keypair("FREEZE_AUTHORITY_PRIVATE_KEY_BASE58")
ix = freeze_account(FreezeAccountParams(program_id=program_id, account=pubkey("TOKEN_ACCOUNT"), mint=pubkey("MINT_ADDRESS"), authority=authority.pubkey()))
send_or_print([ix], signer_env="FREEZE_AUTHORITY_PRIVATE_KEY_BASE58")
'''),
    script("spl_token", "thaw_account", "Thaw token account", '''
from spl.token.instructions import ThawAccountParams, thaw_account

program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
authority = keypair("FREEZE_AUTHORITY_PRIVATE_KEY_BASE58")
ix = thaw_account(ThawAccountParams(program_id=program_id, account=pubkey("TOKEN_ACCOUNT"), mint=pubkey("MINT_ADDRESS"), authority=authority.pubkey()))
send_or_print([ix], signer_env="FREEZE_AUTHORITY_PRIVATE_KEY_BASE58")
'''),
    script("spl_token", "close_account", "Close token account", '''
from spl.token.instructions import CloseAccountParams, close_account

program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
owner = keypair("TOKEN_OWNER_PRIVATE_KEY_BASE58")
ix = close_account(CloseAccountParams(program_id=program_id, account=pubkey("TOKEN_ACCOUNT"), dest=pubkey("DESTINATION_PUBKEY"), owner=owner.pubkey()))
send_or_print([ix], signer_env="TOKEN_OWNER_PRIVATE_KEY_BASE58")
'''),
    script("spl_token", "set_authority", "Set token authority", '''
from spl.token.instructions import AuthorityType, SetAuthorityParams, set_authority

authority_types = {
    "mint": AuthorityType.MINT_TOKENS,
    "freeze": AuthorityType.FREEZE_ACCOUNT,
    "owner": AuthorityType.ACCOUNT_OWNER,
    "close": AuthorityType.CLOSE_ACCOUNT,
}
program_id = pubkey("TOKEN_PROGRAM_ID", env("SPL_TOKEN_PROGRAM_ID", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
current = keypair("CURRENT_AUTHORITY_PRIVATE_KEY_BASE58")
new_authority = Pubkey.from_string(env("NEW_AUTHORITY_PUBKEY")) if env("NEW_AUTHORITY_PUBKEY") else None
ix = set_authority(SetAuthorityParams(program_id=program_id, account=pubkey("ACCOUNT_OR_MINT"), authority=authority_types[env("AUTHORITY_TYPE", "mint")], current_authority=current.pubkey(), new_authority=new_authority))
send_or_print([ix], signer_env="CURRENT_AUTHORITY_PRIVATE_KEY_BASE58")
'''),

    # Token-2022 scripts reuse compatible SPL layouts with Token-2022 program id.
    script("token_2022", "derive_ata", "Derive Token-2022 ATA", '''
program_id = pubkey("TOKEN_2022_PROGRAM_ID", env("TOKEN_2022_PROGRAM_ID", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"))
ata_program = pubkey("ASSOCIATED_TOKEN_PROGRAM_ID", env("ASSOCIATED_TOKEN_PROGRAM_ID", "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"))
ata = Pubkey.find_program_address([bytes(pubkey("OWNER_PUBKEY")), bytes(program_id), bytes(pubkey("MINT_ADDRESS"))], ata_program)[0]
print(ata)
'''),
    script("token_2022", "get_accounts_by_owner", "Get Token-2022 accounts by owner", '''
from solana.rpc.types import TokenAccountOpts

opts = TokenAccountOpts(program_id=pubkey("TOKEN_2022_PROGRAM_ID", env("TOKEN_2022_PROGRAM_ID", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")))
print_response(client().get_token_accounts_by_owner_json_parsed(pubkey("OWNER_PUBKEY"), opts))
'''),
    script("token_2022", "mint_to", "Mint Token-2022 tokens", '''
os.environ["TOKEN_PROGRAM_ID"] = env("TOKEN_2022_PROGRAM_ID", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
exec((Path(__file__).resolve().parents[1] / "spl_token" / "mint_to.py").read_text(encoding="utf-8"))
'''),
    script("token_2022", "burn", "Burn Token-2022 tokens", '''
os.environ["TOKEN_PROGRAM_ID"] = env("TOKEN_2022_PROGRAM_ID", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
exec((Path(__file__).resolve().parents[1] / "spl_token" / "burn.py").read_text(encoding="utf-8"))
'''),
    script("token_2022", "transfer_checked", "Transfer checked Token-2022 tokens", '''
os.environ["TOKEN_PROGRAM_ID"] = env("TOKEN_2022_PROGRAM_ID", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
exec((Path(__file__).resolve().parents[1] / "spl_token" / "transfer_checked.py").read_text(encoding="utf-8"))
'''),
    script("token_2022", "thaw_account", "Thaw Token-2022 account", '''
os.environ["TOKEN_PROGRAM_ID"] = env("TOKEN_2022_PROGRAM_ID", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
exec((Path(__file__).resolve().parents[1] / "spl_token" / "thaw_account.py").read_text(encoding="utf-8"))
'''),
    script("token_2022", "set_authority", "Set Token-2022 authority", '''
os.environ["TOKEN_PROGRAM_ID"] = env("TOKEN_2022_PROGRAM_ID", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
exec((Path(__file__).resolve().parents[1] / "spl_token" / "set_authority.py").read_text(encoding="utf-8"))
'''),

    # Jupiter and metadata helpers.
    script("jupiter", "quote", "Get Jupiter quote", '''
import requests

url = env("JUPITER_QUOTE_URL", "https://quote-api.jup.ag/v6/quote")
params = {
    "inputMint": env("INPUT_MINT", required=True),
    "outputMint": env("OUTPUT_MINT", required=True),
    "amount": env("RAW_AMOUNT", required=True),
    "slippageBps": env("SLIPPAGE_BPS", "50"),
}
print_response(requests.get(url, params=params, timeout=15).json())
'''),
    script("jupiter", "swap_transaction", "Get Jupiter swap transaction", '''
import requests

quote = json.loads(Path(env("QUOTE_JSON_FILE", required=True)).read_text(encoding="utf-8"))
payload = {
    "quoteResponse": quote,
    "userPublicKey": str(keypair().pubkey()),
    "wrapAndUnwrapSol": env_bool("WRAP_AND_UNWRAP_SOL", True),
}
print_response(requests.post(env("JUPITER_SWAP_URL", "https://quote-api.jup.ag/v6/swap"), json=payload, timeout=20).json())
'''),
    script("metadata", "derive_metadata_pda", "Derive Metaplex metadata PDA", '''
metadata_program = pubkey("METADATA_PROGRAM_ID", env("METADATA_PROGRAM_ID", "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"))
metadata_pda = Pubkey.find_program_address([b"metadata", bytes(metadata_program), bytes(pubkey("MINT_ADDRESS"))], metadata_program)[0]
print(metadata_pda)
'''),
]


def render(entry: dict[str, str]) -> str:
    return (
        f'#!/usr/bin/env python\n'
        f'"""\n'
        f'{entry["title"]}.\n\n'
        f'Generated by generate_isolated_scripts.py.\n'
        f'This file is intentionally standalone and loads .env by itself.\n'
        f'"""\n'
        f'{COMMON.strip()}\n\n\n'
        f'def main() -> None:\n'
        f'{indent(entry["body"], 4)}\n\n\n'
        f'if __name__ == "__main__":\n'
        f'    main()\n'
    )


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in text.splitlines())


def write_readme() -> None:
    rows = "\n".join(
        f"- `{entry['category']}/{entry['name']}.py` - {entry['title']}."
        for entry in sorted(SCRIPTS, key=lambda item: (item["category"], item["name"]))
    )
    (OUT / "README.md").write_text(
        (
            "# Isolated Solana Scripts\n\n"
            "Each script in this directory is standalone: it loads `.env`, imports its own dependencies,\n"
            "and runs one focused Solana operation.\n\n"
            "Read-only scripts execute immediately. Transaction-building scripts default to dry-run mode\n"
            "and print their instruction. Set `SEND_TRANSACTION=true` to broadcast.\n\n"
            "## Scripts\n\n"
            f"{rows}\n"
        ),
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for entry in SCRIPTS:
        folder = OUT / entry["category"]
        folder.mkdir(exist_ok=True)
        (folder / f"{entry['name']}.py").write_text(render(entry), encoding="utf-8")
    write_readme()
    print(f"Generated {len(SCRIPTS)} isolated scripts in {OUT}")


if __name__ == "__main__":
    main()
