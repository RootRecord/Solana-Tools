# Solana Wallets Toolkit

Local-first Python tooling for the Solana community.

This project exists to help everyday people use Solana in a cheap, understandable, and secure manner on their own computer. The goal is simple: give users small, inspectable scripts for common Solana tasks instead of forcing them to rely on opaque hosted tools for every wallet, token, and authority operation.

The toolkit is maintained as part of the RootRecord ecosystem. Visit [rootrecord.info](https://rootrecord.info) for RootRecord and [solana.rootrecord.info](https://solana.rootrecord.info) for the public Solana tools site.

## Support The Work

If this helps you learn, audit, recover, or manage your own Solana assets, kind readers can donate here:

```text
Solana: 3QG6gVk3fdimzQaKX9zf7J6kCs5DRLKg1RNea3VBosDJ
```

Donations support continued open tooling, documentation, and practical Solana education for users who want to stay self-custodial.

## What Is Included

- `Roots/solswap.py` - an interactive Jupiter SOL/USDC swap assistant.
- `Roots/RootsMinter.py` - mint tokens to a configured destination wallet.
- `Roots/burn.py` - burn tokens from the configured owner account.
- `Roots/check.py` - check the configured wallet token balance.
- `Roots/unfreeze.py` - inspect and thaw configured token accounts.
- `Roots/transferall.py` - transfer mint authority, freeze authority, and metadata update authority.
- `Roots/transferauthonly.py` - transfer only Metaplex metadata update authority.
- `Roots/MoveAuth.py` - authority transfer script with retry handling.
- `Roots/config.py` - shared `.env` loader and typed Solana config helpers.
- `isolated_scripts/` - 80 standalone one-function scripts grouped by RPC, solders, system, SPL Token, Token-2022, Jupiter, and metadata.
- `generate_isolated_scripts.py` - catalog generator for rebuilding the isolated script suite.
- `solana_tools_dashboard.py` - clean desktop dashboard that loads `.env`, runs actions silently, and streams output into an in-app terminal.
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

Copy the example env file and fill in local values:

```powershell
Copy-Item .env.example .env
```

The real `.env` is ignored by git. Keep it local.

## Environment Variables

Required runtime values live in `.env`:

- `SOLANA_RPC_URL`
- `SOLANA_ACTIVE_PRIVATE_KEY_BASE58`
- `SOLANA_OLD_PRIVATE_KEY_BASE58`
- `ROOTS_MINT_ADDRESS`
- `ROOTS_OWNER_WALLET`
- `ROOTS_DESTINATION_WALLET`
- `ROOTS_NEW_AUTHORITY`
- `ROOTS_TOKENS_TO_MINT`
- `ROOTS_TOKEN_DECIMALS`
- `ROOTS_UNFREEZE_ACCOUNTS`
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

Use `.env.example` as the committed template. Put real secrets only in `.env`.

## Running Scripts

Run scripts from the repository root:

```powershell
python .\Roots\check.py
python .\Roots\RootsMinter.py
python .\Roots\burn.py
python .\Roots\unfreeze.py
python .\Roots\transferall.py
python .\Roots\transferauthonly.py
python .\Roots\MoveAuth.py
python .\Roots\solswap.py
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
```

Read-only scripts run immediately. Scripts that build transactions default to dry-run mode and print the instruction. Set `SEND_TRANSACTION=true` in your environment only when you want to broadcast.

## Solana Tools Dashboard

The dashboard gives everyday users a clean local interface for the same script actions:

```powershell
python .\solana_tools_dashboard.py
```

The app discovers scripts in `isolated_scripts/` and `Roots/`, loads `.env`, runs each selected action in a hidden child process, and displays the full run in an in-app terminal. Actions that build transactions remain in dry-run mode unless `SEND_TRANSACTION=true` is enabled in the dashboard.

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

For more RootRecord work, visit [rootrecord.info](https://rootrecord.info). For public Solana tools and references, visit [solana.rootrecord.info](https://solana.rootrecord.info).

## Git Hygiene

This repository ignores:

- `.env` and local env variants.
- existing `wallets.env`, `tokens.env`, and `tokens.env.txt` files.
- `trading_history.json`.
- Python caches and local virtual environments.

Before committing, verify no secrets are staged:

```powershell
git status --short
git diff --cached
```

Recommended commit message:

```text
chore: prepare solana wallet toolkit for github
```
