# Solana Wallets Toolkit

Local-first Python tooling for the Solana community.

This project exists to help everyday people use Solana in a cheap, understandable, and secure manner on their own computer. The goal is simple: give users small, inspectable scripts for common Solana tasks instead of forcing them to rely on opaque hosted tools for every wallet, token, and authority operation.

## Support The Work

If this helps you learn, audit, recover, or manage your own Solana assets, kind readers can donate here:

```text
Solana: 3QG6gVk3fdimzQaKX9zf7J6kCs5DRLKg1RNea3VBosDJ
```

Donations support continued open tooling, documentation, and practical Solana education for users who want to stay self-custodial.

## What Is Included

- `wallet_actions/jupiter_swap_assistant.py` - an interactive Jupiter SOL/USDC swap assistant.
- `wallet_actions/mint_tokens.py` - mint tokens to a configured destination wallet.
- `wallet_actions/burn_tokens.py` - burn tokens from the configured owner account.
- `wallet_actions/check_token_balance.py` - check the configured wallet token balance.
- `wallet_actions/thaw_token_accounts.py` - inspect and thaw configured token accounts.
- `wallet_actions/transfer_all_authorities.py` - transfer mint authority, freeze authority, and metadata update authority.
- `wallet_actions/transfer_metadata_authority.py` - transfer only Metaplex metadata update authority.
- `wallet_actions/transfer_authorities_retry.py` - authority transfer script with retry handling.
- `wallet_actions/config.py` - shared `.env` loader and typed Solana config helpers.
- `isolated_scripts/` - 113 standalone one-function Python scripts grouped by RPC, solders, system, SPL Token, Token-2022, Jupiter, Raydium, LaunchLab, Meteora, Orca, launchpad discovery, and metadata.
- `ts_actions/` - TypeScript SDK actions for flows that need official SDKs, including Raydium LaunchLab create/buy/sell, Meteora DLMM swaps and positions, and Orca Whirlpool swaps.
- `package.json` / `tsconfig.json` - optional Node SDK runtime for `ts_actions/`.
- `generate_isolated_scripts.py` - catalog generator for rebuilding the isolated script suite.
- `solana_tools_dashboard.py` - clean desktop dashboard that loads `.env`, runs actions silently, and streams output into an in-app terminal.
- `install_dependencies.py` - dependency checker/installer that can be launched from the dashboard terminal.
- `build_exe.ps1` / `build_exe.bat` - build `Solana Tools.exe` with PyInstaller.
- `solana_cli_python_functions.txt` - broad 2026 Solana CLI, Python, SPL Token, and Token-2022 reference.

## Safety Notice

These scripts can sign mainnet transactions. Treat them as self-custody tooling, not demos.

- Never commit `.env`, wallet files, private keys, RPC API keys, or trading history.
- Test every flow on devnet before using mainnet.
- Review every transaction before confirming.
- Disabling token authorities can be permanent.
- Closing accounts or mints can be irreversible.
- Keep private keys on your own machine and rotate any key that was ever exposed.

## Setup

Create and activate a Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The dashboard includes a built-in `.env` editor. On first launch, it opens a setup tutorial so users can paste the RPC URL, active signing wallet, optional managed wallet public keys, and optional managed token mints without manually editing files.

If you prefer setup from PowerShell, copy the example env file and fill in local values:

```powershell
Copy-Item .env.example .env
```

The real `.env` is ignored by git. Keep it local. When an existing `.env` is found, the dashboard confirms the active signing wallet, managed wallets, token mints, cluster, and RPC before continuing.

Install the optional TypeScript SDK dependencies when you want SDK-only launchpad and LP execution:

```powershell
npm install
```

The dashboard can also do this from `Install/Repair Dependencies`.

## Environment Variables

Required runtime values live in `.env`:

- `SOLANA_RPC_URL`
- `SOLANA_ACTIVE_PRIVATE_KEY_BASE58`
- `SOLANA_OLD_PRIVATE_KEY_BASE58`
- `ACTIVE_WALLET_LABEL`
- `MANAGED_WALLET_PUBLIC_KEYS`
- `MANAGED_TOKEN_MINTS`
- `DEFAULT_TOKEN_MINT`
- `DEFAULT_OWNER_WALLET`
- `DEFAULT_DESTINATION_WALLET`
- `DEFAULT_NEW_AUTHORITY`
- `DEFAULT_TOKENS_TO_MINT`
- `DEFAULT_TOKEN_DECIMALS`
- `DEFAULT_THAW_ACCOUNTS`
- `SPL_TOKEN_PROGRAM_ID`
- `TOKEN_2022_PROGRAM_ID`
- `ASSOCIATED_TOKEN_PROGRAM_ID`
- `METADATA_PROGRAM_ID`
- `SOL_MINT`
- `USDC_MINT`
- `TRADING_HISTORY_FILE`
- `SOL_PRICE_FALLBACK`
- `JUPITER_QUOTE_URL`
- `JUPITER_SWAP_URL`
- `COINGECKO_SOL_PRICE_URL`
- Raydium, LaunchLab, Meteora, Orca, TypeScript SDK, and generic LP API values shown in `.env.example`

Use `.env.example` as the committed template. Put real secrets only in `.env`.

## Running Scripts

Run wallet action scripts from the repository root:

```powershell
python .\wallet_actions\check_token_balance.py
python .\wallet_actions\mint_tokens.py
python .\wallet_actions\burn_tokens.py
python .\wallet_actions\thaw_token_accounts.py
python .\wallet_actions\transfer_all_authorities.py
python .\wallet_actions\transfer_metadata_authority.py
python .\wallet_actions\transfer_authorities_retry.py
python .\wallet_actions\jupiter_swap_assistant.py
```

## Running Isolated Scripts

Each file under `isolated_scripts/` is intentionally standalone. It loads `.env` by itself and performs one focused operation. This keeps the examples easy to read, copy, audit, and adapt.

Examples:

```powershell
python .\isolated_scripts\rpc\get_balance.py
python .\isolated_scripts\solders\derive_pda.py
python .\isolated_scripts\spl_token\derive_ata.py
python .\isolated_scripts\token_2022\get_accounts_by_owner.py
python .\isolated_scripts\jupiter\quote.py
python .\isolated_scripts\raydium\swap_quote_base_in.py
python .\isolated_scripts\meteora\dlmm_pair_all.py
python .\isolated_scripts\orca\search_pools.py
```

Read-only scripts run immediately. Scripts that build transactions default to dry-run mode, print the instruction, and estimate the network fee before any broadcast. When running from the dashboard, use `Preview Selected` first, review the built-in terminal output, then click `Confirm/Execute Preview` to broadcast that same action.

## Raydium And LP Launchpads

The dashboard includes practical LP and launchpad actions that can be performed safely from Python and, where needed, official TypeScript SDKs:

- Raydium API v3 reads: mint metadata, mint prices, pool lists, pool lookup by IDs, and pool lookup by mint pair.
- Raydium Trade API: exact-input quotes, exact-output quotes, build swap transactions, and sign/send built transactions when explicitly enabled.
- Raydium LaunchLab: Mint API reads, History API reads, launch status checks, auth-token request helper, and signed Forum API GET/POST helpers.
- Meteora: DLMM pair discovery, DLMM pool reads, DAMM v2 pool reads, and a note action for SDK-only swap/position workflows.
- Orca: Whirlpool list, search, and pool detail reads, plus a note action for SDK-only swap/position workflows.
- Generic launchpad helpers: DexScreener search, token-pair lookup, pair lookup, generic GET, and dry-run-first JSON POST.
- TypeScript SDK actions: Raydium LaunchLab create/buy/sell, Meteora DLMM swap/create position/close position, and Orca Whirlpool swap.

SDK actions stay dry-run-first. They quote or build the transaction, print the planned action and estimated network fee in the in-app terminal, and only broadcast after the dashboard confirmation step. If an SDK does not expose the final transaction before execution, the terminal says the fee estimate is unavailable and still requires explicit confirmation before broadcast.

## Solana Tools Dashboard

The dashboard gives everyday users a clean local interface for the same script actions:

```powershell
python .\solana_tools_dashboard.py
```

The app discovers scripts in `isolated_scripts/`, `wallet_actions/`, and `ts_actions/`, loads `.env`, runs each selected action in a hidden child process, and displays the full run in an in-app terminal. Transaction actions use a two-step flow:

1. `Preview Selected` builds or quotes the action, prints estimated network cost, and broadcasts nothing.
2. `Confirm/Execute Preview` reruns the same action with broadcast enabled only after user confirmation.

For command-line use, scripts still refuse to broadcast until `SEND_TRANSACTION=true` is set and the user types `EXECUTE` when prompted.

The `Edit .env` button opens the built-in editor at any time. It masks private key fields by default, can reveal them on request, writes `.env` locally, and displays the derived active signing wallet plus any managed wallets or token mints after saving.

The packaged exe is self-contained for Python dashboard use. TypeScript SDK actions require Node.js and the npm packages from `package.json`; the `Install/Repair Dependencies` button checks that setup and prompts before installing anything.

Build the Windows executable:

```powershell
.\build_exe.ps1
```

The exe is written to:

```text
dist\Solana Tools\Solana Tools.exe
```

The real `.env` is not bundled. Copy `.env.example` to `.env` next to the exe and fill in your own local values before running private or transaction actions.

## Token-2022 Notes

The current operational scripts are configured for the classic SPL Token program by default:

```text
TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
```

Token-2022 support is documented in `solana_cli_python_functions.txt`. To target Token-2022, update the relevant program ID and ATA derivation variables:

```text
TOKEN_2022_PROGRAM_ID=TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb
```

Some Token-2022 extensions require the `spl-token` CLI, TypeScript, Rust, or raw instruction builders depending on Python package support.

## Community Purpose

Solana is most useful when people can actually use it themselves. This repository is meant to support that by keeping operations local, transparent, and low cost:

- Local: scripts run on your computer with your own keys and RPC settings.
- Transparent: each operation is plain Python you can inspect before running.
- Cheap: direct RPC and CLI-style workflows avoid unnecessary middlemen.
- Educational: isolated scripts show one Solana concept at a time.
- Self-custodial: secrets stay in your local `.env`, not in hosted dashboards.

## Git Hygiene

This repository ignores:

- `.env` and local env variants.
- existing `wallets.env`, `tokens.env`, and `tokens.env.txt` files.
- `trading_history.json`.
- Python caches and local virtual environments.
- `node_modules/` and local npm cache folders.

Before committing, verify no secrets are staged:

```powershell
git status --short
git diff --cached
```

Recommended commit message:

```text
chore: prepare solana wallet toolkit for github
```
