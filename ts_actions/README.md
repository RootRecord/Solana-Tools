# TypeScript SDK Actions

These actions cover Solana flows where the Python SDKs are not the practical source of truth.
They are discovered by `solana_tools_dashboard.py` and can also be run directly.

Install dependencies:

```powershell
npm install
```

Run an action:

```powershell
npm exec -- tsx .\ts_actions\raydium_launchlab_create.ts
npm exec -- tsx .\ts_actions\meteora_dlmm_swap.ts
npm exec -- tsx .\ts_actions\orca_whirlpool_swap.ts
```

Actions read `.env` from the repo or exe directory. They default to dry-run mode and print
the quote plus estimated network fee when the SDK exposes the built transaction. Broadcasts
require the dashboard's `Confirm/Execute Preview` step, or `SEND_TRANSACTION=true` plus
typing `EXECUTE` when running directly from a terminal.
