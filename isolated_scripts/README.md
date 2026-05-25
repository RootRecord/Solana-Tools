# Isolated Solana Scripts

Each script in this directory is standalone: it loads `.env`, imports its own dependencies,
and runs one focused Solana operation.

Read-only scripts execute immediately. Transaction-building scripts default to dry-run mode
and print their instruction. Set `SEND_TRANSACTION=true` to broadcast.

## Scripts

- `jupiter/quote.py` - Get Jupiter quote.
- `jupiter/swap_transaction.py` - Get Jupiter swap transaction.
- `metadata/derive_metadata_pda.py` - Derive Metaplex metadata PDA.
- `rpc/get_account_info.py` - Get raw account info.
- `rpc/get_account_info_json_parsed.py` - Get parsed account info.
- `rpc/get_balance.py` - Get SOL balance.
- `rpc/get_block.py` - Get block by slot.
- `rpc/get_block_commitment.py` - Get block commitment.
- `rpc/get_block_height.py` - Get current block height.
- `rpc/get_block_time.py` - Get block time.
- `rpc/get_blocks.py` - Get block slots.
- `rpc/get_cluster_nodes.py` - Get cluster nodes.
- `rpc/get_epoch_info.py` - Get epoch info.
- `rpc/get_epoch_schedule.py` - Get epoch schedule.
- `rpc/get_fee_for_message.py` - Get fee for a simple message.
- `rpc/get_first_available_block.py` - Get first available block.
- `rpc/get_genesis_hash.py` - Get genesis hash.
- `rpc/get_identity.py` - Get RPC node identity.
- `rpc/get_inflation_governor.py` - Get inflation governor.
- `rpc/get_inflation_rate.py` - Get inflation rate.
- `rpc/get_inflation_reward.py` - Get inflation reward.
- `rpc/get_largest_accounts.py` - Get largest SOL accounts.
- `rpc/get_latest_blockhash.py` - Get latest blockhash.
- `rpc/get_minimum_balance_for_rent_exemption.py` - Get rent exemption amount.
- `rpc/get_multiple_accounts.py` - Get multiple accounts.
- `rpc/get_multiple_accounts_json_parsed.py` - Get multiple parsed accounts.
- `rpc/get_program_accounts.py` - Get program accounts.
- `rpc/get_program_accounts_json_parsed.py` - Get parsed program accounts.
- `rpc/get_recent_performance_samples.py` - Get performance samples.
- `rpc/get_signature_statuses.py` - Get signature statuses.
- `rpc/get_signatures_for_address.py` - Get signatures for address.
- `rpc/get_slot.py` - Get current slot.
- `rpc/get_slot_leader.py` - Get slot leader.
- `rpc/get_slot_leaders.py` - Get slot leaders.
- `rpc/get_supply.py` - Get SOL supply.
- `rpc/get_token_account_balance.py` - Get token account balance.
- `rpc/get_token_accounts_by_delegate.py` - Get token accounts by delegate.
- `rpc/get_token_accounts_by_delegate_json_parsed.py` - Get parsed token accounts by delegate.
- `rpc/get_token_accounts_by_owner.py` - Get token accounts by owner.
- `rpc/get_token_accounts_by_owner_json_parsed.py` - Get parsed token accounts by owner.
- `rpc/get_token_largest_accounts.py` - Get largest token accounts.
- `rpc/get_token_supply.py` - Get token supply.
- `rpc/get_transaction.py` - Get transaction details.
- `rpc/get_transaction_count.py` - Get transaction count.
- `rpc/get_version.py` - Get RPC node version.
- `rpc/get_vote_accounts.py` - Get vote accounts.
- `rpc/is_connected.py` - Check RPC health.
- `rpc/request_airdrop.py` - Request devnet/testnet airdrop.
- `rpc/simulate_sol_transfer.py` - Simulate a SOL transfer.
- `solders/build_raw_instruction.py` - Build a raw instruction preview.
- `solders/create_with_seed.py` - Create seeded address.
- `solders/derive_pda.py` - Derive PDA from string seeds.
- `solders/generate_keypair.py` - Generate a new keypair.
- `solders/parse_pubkey.py` - Parse and print a pubkey.
- `solders/parse_signature.py` - Parse and print a signature.
- `solders/sign_message.py` - Sign arbitrary message.
- `solders/versioned_transaction_from_base64.py` - Parse versioned transaction bytes.
- `spl_token/approve.py` - Approve token delegate.
- `spl_token/burn.py` - Burn tokens.
- `spl_token/close_account.py` - Close token account.
- `spl_token/create_associated_token_account.py` - Create associated token account.
- `spl_token/derive_ata.py` - Derive associated token account.
- `spl_token/freeze_account.py` - Freeze token account.
- `spl_token/mint_to.py` - Mint tokens.
- `spl_token/revoke.py` - Revoke token delegate.
- `spl_token/set_authority.py` - Set token authority.
- `spl_token/thaw_account.py` - Thaw token account.
- `spl_token/transfer_checked.py` - Transfer checked tokens.
- `system/allocate.py` - Allocate account space.
- `system/assign.py` - Assign account owner.
- `system/create_account.py` - Create system account.
- `system/transfer_sol.py` - Transfer SOL.
- `system/transfer_with_seed.py` - Transfer SOL from seeded account.
- `token_2022/burn.py` - Burn Token-2022 tokens.
- `token_2022/derive_ata.py` - Derive Token-2022 ATA.
- `token_2022/get_accounts_by_owner.py` - Get Token-2022 accounts by owner.
- `token_2022/mint_to.py` - Mint Token-2022 tokens.
- `token_2022/set_authority.py` - Set Token-2022 authority.
- `token_2022/thaw_account.py` - Thaw Token-2022 account.
- `token_2022/transfer_checked.py` - Transfer checked Token-2022 tokens.
