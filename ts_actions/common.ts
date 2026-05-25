import fs from "node:fs";
import path from "node:path";
import process from "node:process";
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
  if (!envBool("SEND_TRANSACTION")) {
    console.log("DRY RUN: set SEND_TRANSACTION=true to broadcast.");
    console.log(tx);
    return;
  }

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

export function sdkNote(name: string, details: string): void {
  printJson({
    sdk: name,
    status: "ready",
    sendTransaction: envBool("SEND_TRANSACTION"),
    details,
  });
}
