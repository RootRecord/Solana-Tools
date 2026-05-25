from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solders.transaction import VersionedTransaction
import base58
import requests
import json
import os
import time
import threading
from datetime import datetime
from config import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    COINGECKO_SOL_PRICE_URL,
    JUPITER_QUOTE_URL,
    JUPITER_SWAP_URL,
    RPC_URL,
    SOL_MINT,
    SOL_PRICE_FALLBACK,
    SPL_TOKEN_PROGRAM_ID,
    TRADING_HISTORY_FILE,
    USDC_MINT,
    keypair_from_env,
)

print("🚀 Advanced Jupiter Trading Assistant + Resilient Network\n")

# ================== CONFIG ==================
SOL = SOL_MINT
USDC = USDC_MINT
HISTORY_FILE = TRADING_HISTORY_FILE

client = Client(RPC_URL)
payer = keypair_from_env("SOLANA_ACTIVE_PRIVATE_KEY_BASE58")

current_sol_price = SOL_PRICE_FALLBACK  # Safe fallback

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    initial_sol = get_sol_balance()
    return {
        "profile": {"wallet": str(payer.pubkey()), "created_at": datetime.now().isoformat(), "initial_sol": initial_sol},
        "trades": [],
        "last_buy_price": 0,
        "last_sell_price": 0,
        "total_bought": 0,
        "total_sold": 0,
    }

def save_history(data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_sol_balance():
    return client.get_balance(payer.pubkey()).value / 1_000_000_000

def get_usdc_balance():
    try:
        ata = Pubkey.find_program_address(
            [bytes(payer.pubkey()), bytes(SPL_TOKEN_PROGRAM_ID), bytes(USDC)],
            ASSOCIATED_TOKEN_PROGRAM_ID,
        )[0]
        resp = client.get_token_account_balance(ata)
        return float(resp.value.ui_amount or 0)
    except:
        return 0.0

def fetch_sol_price():
    global current_sol_price
    # Try Jupiter
    try:
        quote = requests.get(
            f"{JUPITER_QUOTE_URL}?inputMint={SOL}&outputMint={USDC}&amount=1000000000",
            timeout=8,
        ).json()
        if 'outAmount' in quote:
            current_sol_price = float(quote['outAmount']) / 1_000_000
            return
    except:
        pass

    # Fallback CoinGecko
    try:
        data = requests.get(COINGECKO_SOL_PRICE_URL, timeout=8).json()
        current_sol_price = data.get("solana", {}).get("usd", current_sol_price)
    except:
        pass  # Keep previous price

def main():
    global current_sol_price
    history = load_history()

    print("Fetching current SOL price...")
    fetch_sol_price()

    threading.Thread(target=lambda: [time.sleep(300), fetch_sol_price()] * 999, daemon=True).start()  # Background

    while True:
        sol_bal = get_sol_balance()
        usdc_bal = get_usdc_balance()
        portfolio = usdc_bal + (sol_bal * current_sol_price)
        initial_value = history.get("profile", {}).get("initial_sol", 0) * current_sol_price

        print("\n" + "="*85)
        print(f"Wallet : {payer.pubkey()}")
        print(f"💰 SOL   : {sol_bal:.6f} SOL")
        print(f"💵 USDC  : {usdc_bal:.4f} USDC")
        print(f"💵 Value : ${portfolio:.2f} | Started: ${initial_value:.2f}")
        print(f"📈 SOL   : ${current_sol_price:.2f} USD")
        print("="*85)

        trades = history.get("trades", [])
        win_rate = (sum(1 for t in trades if t.get("pnl", 0) > 0) / len(trades) * 100) if trades else 0
        total_pnl = sum(t.get("pnl", 0) for t in trades)

        print(f"📊 Trades: {len(trades)} | Win Rate: {win_rate:.1f}% | Total PnL: ${total_pnl:.2f}")

        action = input("\nS = Sell SOL → USDC | B = Buy SOL with USDC | Q = Quit: ").strip().upper()

        if action == 'Q':
            print("👋 Session ended.")
            break

        if action not in ['S', 'B']:
            continue

        percent = int(input("Percentage (1-100): "))
        if percent < 1 or percent > 100:
            continue

        if action == 'S':
            amount = sol_bal * (percent / 100)
            input_mint, output_mint = SOL, USDC
            in_amount = int(amount * 1_000_000_000)
        else:
            amount = usdc_bal * (percent / 100)
            input_mint, output_mint = USDC, SOL
            in_amount = int(amount * 1_000_000)

        # Get Quote with retry
        for attempt in range(3):
            try:
                quote = requests.get(
                    f"{JUPITER_QUOTE_URL}?inputMint={input_mint}&outputMint={output_mint}&amount={in_amount}&slippageBps=50",
                    timeout=10,
                ).json()
                break
            except:
                print(f"Quote attempt {attempt+1} failed, retrying...")
                time.sleep(2)
        else:
            print("Could not get quote. Check internet.")
            continue

        out_amount = float(quote['outAmount']) / (1_000_000 if action == 'S' else 1_000_000_000)
        price = in_amount / float(quote['outAmount']) if action == 'B' else float(quote['outAmount']) / in_amount

        print(f"Expected: {out_amount:.6f} {'USDC' if action == 'S' else 'SOL'} @ ${price:.4f}")

        if input("Confirm? (y/n): ").strip().lower() != 'y':
            continue

        # Execute (same as before)
        try:
            swap_resp = requests.post(JUPITER_SWAP_URL, json={
                "quoteResponse": quote,
                "userPublicKey": str(payer.pubkey()),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 1000
            }, timeout=15).json()

            tx = VersionedTransaction.from_bytes(base58.b58decode(swap_resp['swapTransaction']))
            tx.sign([payer])
            result = client.send_raw_transaction(bytes(tx), opts=TxOpts(skip_preflight=True))

            print(f"\n✅ SUCCESS! Tx: {result.value}")
        except Exception as e:
            print(f"Swap failed: {e}")
            continue

        # Save trade
        trade = {"timestamp": datetime.now().isoformat(), "action": "SELL" if action == 'S' else "BUY", "amount": float(amount), "price": float(price)}
        history.setdefault("trades", []).append(trade)

        if action == 'B':
            history["last_buy_price"] = float(price)
        else:
            history["last_sell_price"] = float(price)

        save_history(history)

if __name__ == "__main__":
    main()