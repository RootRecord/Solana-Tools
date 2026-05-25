import BN from "bn.js";
import * as Meteora from "@meteora-ag/dlmm";
import { StrategyType } from "@meteora-ag/dlmm";
import { Keypair, PublicKey } from "@solana/web3.js";
import { connection, env, envInt, keypair, printJson, sendOrDescribeTransaction } from "./common.js";

const DLMM = (Meteora as any).default;
const conn = connection();
const user = keypair();
const poolAddress = new PublicKey(env("METEORA_POOL_ADDRESS", undefined, true));
const position = Keypair.generate();
const dlmmPool = await DLMM.create(conn, poolAddress);

const strategyName = env("METEORA_STRATEGY_TYPE", "Spot");
const strategyType = (StrategyType as any)[strategyName] ?? StrategyType.Spot;

const tx = await dlmmPool.initializePositionAndAddLiquidityByStrategy({
  positionPubKey: position.publicKey,
  user: user.publicKey,
  totalXAmount: new BN(env("RAW_X_AMOUNT", "0")),
  totalYAmount: new BN(env("RAW_Y_AMOUNT", "0")),
  strategy: {
    minBinId: envInt("MIN_BIN_ID"),
    maxBinId: envInt("MAX_BIN_ID"),
    strategyType,
  },
  slippage: envInt("SLIPPAGE_BPS", 50),
});

printJson({
  pool: poolAddress,
  position: position.publicKey,
  strategy: strategyName,
  minBinId: envInt("MIN_BIN_ID"),
  maxBinId: envInt("MAX_BIN_ID"),
});

await sendOrDescribeTransaction(tx, [user, position]);
