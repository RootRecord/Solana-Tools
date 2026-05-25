import BN from "bn.js";
import {
  DEV_LAUNCHPAD_PROGRAM,
  LAUNCHPAD_PROGRAM,
  Raydium,
  TxVersion,
} from "@raydium-io/raydium-sdk-v2";
import { PublicKey } from "@solana/web3.js";
import { connection, env, envBool, keypair, printJson } from "./common.js";

const owner = keypair();
const conn = connection();
const cluster = env("SOLANA_CLUSTER", "mainnet-beta");
const raydiumCluster = cluster === "devnet" ? "devnet" : "mainnet";
const programId = env("RAYDIUM_LAUNCHPAD_PROGRAM_ID")
  ? new PublicKey(env("RAYDIUM_LAUNCHPAD_PROGRAM_ID"))
  : raydiumCluster === "devnet"
    ? DEV_LAUNCHPAD_PROGRAM
    : LAUNCHPAD_PROGRAM;

const raydium = await Raydium.load({
  owner,
  connection: conn,
  cluster: raydiumCluster,
  disableFeatureCheck: true,
  disableLoadToken: false,
});

const mintA = new PublicKey(env("TOKEN_MINT", undefined, true));
const poolId = new PublicKey(env("RAYDIUM_LAUNCHPAD_POOL_ID", undefined, true));
const poolInfo = await (raydium.launchpad as any).getPoolInfoFromRpc(poolId);
const mintInfo = await raydium.token.getTokenInfo(mintA);

const { execute, extInfo } = await raydium.launchpad.sellToken({
  programId,
  mintA,
  mintAProgram: new PublicKey((mintInfo as any).programId),
  poolInfo,
  configInfo: (poolInfo as any).configInfo,
  txVersion: TxVersion.V0,
  sellAmount: new BN(env("RAW_AMOUNT", undefined, true)),
  slippage: new BN(env("SLIPPAGE_BPS", "100")),
} as any);

printJson({
  poolId,
  mintA,
  expectedReceiveAmount: (extInfo as any)?.decimalOutAmount ?? extInfo,
  dryRun: !envBool("SEND_TRANSACTION"),
});

if (!envBool("SEND_TRANSACTION")) {
  console.log("DRY RUN: set SEND_TRANSACTION=true to sell into this LaunchLab pool.");
  process.exit(0);
}

const sentInfo = await execute({ sendAndConfirm: true } as any);
printJson(sentInfo);
