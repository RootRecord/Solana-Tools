import BN from "bn.js";
import * as Meteora from "@meteora-ag/dlmm";
import { PublicKey } from "@solana/web3.js";
import { connection, env, envBool, keypair, printJson, sendOrDescribeTransaction } from "./common.js";

const DLMM = (Meteora as any).default;
const conn = connection();
const user = keypair();
const poolAddress = new PublicKey(env("METEORA_POOL_ADDRESS", undefined, true));
const swapAmount = new BN(env("RAW_AMOUNT", undefined, true));
const swapForY = envBool("SWAP_FOR_Y", true);
const allowedSlippageBps = new BN(env("SLIPPAGE_BPS", "50"));

const dlmmPool = await DLMM.create(conn, poolAddress);
const binArrays = await dlmmPool.getBinArrayForSwap(swapForY);
const quote = dlmmPool.swapQuote(swapAmount, swapForY, allowedSlippageBps, binArrays);

printJson({
  pool: poolAddress,
  swapForY,
  inAmount: swapAmount,
  outAmount: quote.outAmount,
  minOutAmount: quote.minOutAmount,
  fee: quote.fee,
  priceImpact: quote.priceImpact,
});

const tx = await dlmmPool.swap({
  inToken: swapForY ? dlmmPool.tokenX.publicKey : dlmmPool.tokenY.publicKey,
  outToken: swapForY ? dlmmPool.tokenY.publicKey : dlmmPool.tokenX.publicKey,
  inAmount: swapAmount,
  minOutAmount: quote.minOutAmount,
  lbPair: dlmmPool.pubkey,
  user: user.publicKey,
  binArraysPubkey: quote.binArraysPubkey,
});

await sendOrDescribeTransaction(tx, [user]);
