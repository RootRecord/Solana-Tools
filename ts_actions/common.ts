import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { createInterface } from "node:readline/promises";
import dotenv from "dotenv";
import bs58 from "bs58";
import {
  Connection,
  Keypair,
  PublicKey,
  Transaction,
  VersionedTransaction,
  sendAndConfirmTransaction,
} from "@solana/web3.js";

export function loadEnv(): void {
  const roots = [process.cwd(), path.resolve(import.meta.dirname, "..")];
  for (const root of roots) {
    const envPath = path.join(root, ".env");
    if (fs.existsSync(envPath)) {
      dotenv.config({ path: envPath, override: false });
    }
  }
}

loadEnv();

export function env(name: string, fallback?: string, required = false): string {
  const value = process.env[name] ?? fallback ?? "";
  if (required && !value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export function envInt(name: string, fallback = 0): number {
  return Number.parseInt(env(name, String(fallback)), 10);
}

export function envBigInt(name: string, fallback = "0"): bigint {
  return BigInt(env(name, fallback));
}

export function envBool(name: string, fallback = false): boolean {
  const value = env(name, fallback ? "true" : "false").toLowerCase();
  return ["1", "true", "yes", "y", "on"].includes(value);
}

export function envJson<T = unknown>(name: string, fallback: T): T {
  const value = env(name);
  return value ? JSON.parse(value) as T : fallback;
}

export function keypair(name = "SOLANA_ACTIVE_PRIVATE_KEY_BASE58"): Keypair {
  return Keypair.fromSecretKey(bs58.decode(env(name, undefined, true)));
}

export function pubkey(name: string, fallback?: string): PublicKey {
  return new PublicKey(env(name, fallback, true));
}

export function connection(): Connection {
  return new Connection(env("SOLANA_RPC_URL", "https://api.devnet.solana.com"), "confirmed");
}

export function printJson(value: unknown): void {
  console.log(JSON.stringify(value, (_key, val) => {
    if (typeof val === "bigint") return val.toString();
    if (val instanceof PublicKey) return val.toBase58();
    if (val instanceof Keypair) return val.publicKey.toBase58();
    if (val && typeof val === "object" && "toBase58" in val && typeof (val as any).toBase58 === "function") {
      return (val as any).toBase58();
    }
    if (val && typeof val === "object" && "toString" in val && val.constructor?.name === "BN") {
      return val.toString();
    }
    return val;
  }, 2));
}

export async function sendOrDescribeTransaction(
  tx: Transaction | VersionedTransaction,
  signers: Keypair[] = [keypair()],
): Promise<void> {
  const feeLamports = await estimateAndPrintTransactionCost(tx, signers[0]);
  if (!envBool("SEND_TRANSACTION")) {
    console.log("DRY RUN: no transaction was broadcast.");
    console.log(tx);
    return;
  }

  await requireTransactionConfirmation(feeLamports);

  const conn = connection();
  if (tx instanceof VersionedTransaction) {
    tx.sign(signers);
    const sig = await conn.sendRawTransaction(tx.serialize(), { skipPreflight: false });
    await conn.confirmTransaction(sig, "confirmed");
    console.log(sig);
    return;
  }

  const sig = await sendAndConfirmTransaction(conn, tx, signers, { skipPreflight: false });
  console.log(sig);
}

export async function estimateAndPrintTransactionCost(
  txOrTxs: unknown,
  payer: Keypair = keypair(),
): Promise<number | null> {
  const txs = flattenTransactions(txOrTxs);
  if (!txs.length) {
    console.log("Estimated network fee: unavailable. The SDK did not expose the built transaction before execution.");
    console.log("Review quoted token amounts, rent deposits, and platform fees printed above before confirming.");
    return null;
  }

  let total = 0;
  for (const [index, tx] of txs.entries()) {
    const fee = await estimateSingleTransactionFee(tx, payer);
    if (fee === null) {
      console.log(`Estimated network fee for transaction ${index + 1}: unavailable.`);
      return null;
    }
    total += fee;
    console.log(`Estimated network fee for transaction ${index + 1}: ${fee} lamports (${fee / 1_000_000_000} SOL)`);
  }
  console.log(`Estimated total network fee: ${total} lamports (${total / 1_000_000_000} SOL)`);
  console.log("Estimate excludes token amounts, rent deposits, DEX/platform fees, and later priority-fee changes unless the action prints them separately.");
  return total;
}

export async function requireTransactionConfirmation(feeLamports: number | null): Promise<void> {
  const feeText = feeLamports === null
    ? "network fee unavailable"
    : `${feeLamports} lamports (${feeLamports / 1_000_000_000} SOL)`;
  if (envBool("SOLANA_TOOLS_USER_CONFIRMED")) {
    console.log(`Dashboard confirmation received. Proceeding with broadcast. Estimated ${feeText}.`);
    return;
  }

  const rl = createInterface({ input: process.stdin, output: process.stdout });
  try {
    const answer = await rl.question(`Type EXECUTE to broadcast this transaction. Estimated ${feeText}: `);
    if (answer.trim() !== "EXECUTE") {
      throw new Error("Transaction cancelled before broadcast.");
    }
  } finally {
    rl.close();
  }
}

function flattenTransactions(value: unknown): Array<Transaction | VersionedTransaction> {
  if (!value) return [];
  if (value instanceof Transaction || value instanceof VersionedTransaction) return [value];
  if (Array.isArray(value)) return value.flatMap((item) => flattenTransactions(item));
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    return [
      ...flattenTransactions(obj.transaction),
      ...flattenTransactions(obj.transactions),
      ...flattenTransactions(obj.tx),
      ...flattenTransactions(obj.txs),
    ];
  }
  return [];
}

async function estimateSingleTransactionFee(
  tx: Transaction | VersionedTransaction,
  payer: Keypair,
): Promise<number | null> {
  const conn = connection();
  try {
    if (tx instanceof VersionedTransaction) {
      const fee = await conn.getFeeForMessage(tx.message, "confirmed");
      return fee.value ?? null;
    }

    if (!tx.feePayer) tx.feePayer = payer.publicKey;
    if (!tx.recentBlockhash) tx.recentBlockhash = (await conn.getLatestBlockhash("confirmed")).blockhash;
    const fee = await conn.getFeeForMessage(tx.compileMessage(), "confirmed");
    return fee.value ?? null;
  } catch (error) {
    console.log(`Fee estimate failed: ${error}`);
    return null;
  }
}

export function sdkNote(name: string, details: string): void {
  printJson({
    sdk: name,
    status: "ready",
    sendTransaction: envBool("SEND_TRANSACTION"),
    details,
  });
}
