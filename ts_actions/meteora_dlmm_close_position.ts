import * as Meteora from "@meteora-ag/dlmm";
import { PublicKey } from "@solana/web3.js";
import { connection, env, keypair, printJson, sendOrDescribeTransaction } from "./common.js";

const DLMM = (Meteora as any).default;
const conn = connection();
const user = keypair();
const poolAddress = new PublicKey(env("METEORA_POOL_ADDRESS", undefined, true));
const positionAddress = new PublicKey(env("POSITION_ADDRESS", undefined, true));
const dlmmPool = await DLMM.create(conn, poolAddress);

const position = await dlmmPool.getPosition(positionAddress);
const tx = await dlmmPool.closePosition({
  owner: user.publicKey,
  position,
});

printJson({
  pool: poolAddress,
  position: positionAddress,
  note: "Position must have zero liquidity before closing.",
});

await sendOrDescribeTransaction(tx, [user]);
