import BN from "bn.js";
import {
  DEV_LAUNCHPAD_PROGRAM,
  getPdaLaunchpadConfigId,
  LAUNCHPAD_PROGRAM,
  LaunchpadConfig,
  Raydium,
  TxVersion,
} from "@raydium-io/raydium-sdk-v2";
import { NATIVE_MINT } from "@solana/spl-token";
import { Keypair, PublicKey } from "@solana/web3.js";
import {
  connection,
  env,
  envBool,
  envInt,
  envJson,
  estimateAndPrintTransactionCost,
  keypair,
  printJson,
  requireTransactionConfirmation,
} from "./common.js";

const owner = keypair();
const conn = connection();
const cluster = env("SOLANA_CLUSTER", "mainnet-beta");
const raydiumCluster = cluster === "devnet" ? "devnet" : "mainnet";
const programId = env("RAYDIUM_LAUNCHPAD_PROGRAM_ID")
  ? new PublicKey(env("RAYDIUM_LAUNCHPAD_PROGRAM_ID"))
  : raydiumCluster === "devnet"
    ? DEV_LAUNCHPAD_PROGRAM
    : LAUNCHPAD_PROGRAM;
const quoteMint = new PublicKey(env("QUOTE_MINT", NATIVE_MINT.toBase58()));
const configId = env("RAYDIUM_LAUNCHPAD_CONFIG_ID")
  ? new PublicKey(env("RAYDIUM_LAUNCHPAD_CONFIG_ID"))
  : getPdaLaunchpadConfigId(programId, quoteMint, envInt("RAYDIUM_LAUNCHPAD_CONFIG_INDEX", 0), 0).publicKey;

const configData = await conn.getAccountInfo(configId);
if (!configData) throw new Error(`LaunchLab config not found: ${configId.toBase58()}`);
const configInfo = LaunchpadConfig.decode(configData.data);

const raydium = await Raydium.load({
  owner,
  connection: conn,
  cluster: raydiumCluster,
  disableFeatureCheck: true,
  disableLoadToken: true,
});

const mintA = Keypair.generate();
const fees = envJson("RAYDIUM_LAUNCHPAD_FEES_JSON", {
  buyNumerator: "100",
  buyDenominator: "10000",
  sellNumerator: "100",
  sellDenominator: "10000",
  lpShare: "60",
  creatorShare: "20",
  protocolShare: "20",
  totalShare: "100",
});

const launch = await raydium.launchpad.createLaunchpad({
  programId,
  mintA: mintA.publicKey,
  decimals: envInt("TOKEN_DECIMALS", 6),
  name: env("TOKEN_NAME", undefined, true),
  symbol: env("TOKEN_SYMBOL", undefined, true),
  uri: env("TOKEN_METADATA_URI", undefined, true),
  migrateType: env("RAYDIUM_MIGRATE_TYPE", "amm") as any,
  configId,
  configInfo,
  supply: new BN(env("TOKEN_SUPPLY_RAW", "1000000000000000")),
  totalSellA: new BN(env("RAYDIUM_TOTAL_SELL_A_RAW", "0")),
  totalFundRaisingB: new BN(env("RAYDIUM_TOTAL_FUND_RAISING_B_RAW", "0")),
  totalLockedAmount: new BN(env("RAYDIUM_TOTAL_LOCKED_AMOUNT_RAW", "0")),
  cliffPeriod: new BN(env("RAYDIUM_CLIFF_PERIOD_SECONDS", "0")),
  unlockPeriod: new BN(env("RAYDIUM_UNLOCK_PERIOD_SECONDS", "0")),
  curveType: envInt("RAYDIUM_CURVE_TYPE", 0),
  graduationFractionBps: envInt("RAYDIUM_GRADUATION_FRACTION_BPS", 8000),
  initialK: new BN(env("RAYDIUM_INITIAL_K", "40")),
  quoteMint,
  openTime: new BN(env("RAYDIUM_OPEN_TIME", String(Math.floor(Date.now() / 1000) + 60))),
  fees: {
    buyNumerator: new BN((fees as any).buyNumerator),
    buyDenominator: new BN((fees as any).buyDenominator),
    sellNumerator: new BN((fees as any).sellNumerator),
    sellDenominator: new BN((fees as any).sellDenominator),
    lpShare: new BN((fees as any).lpShare),
    creatorShare: new BN((fees as any).creatorShare),
    protocolShare: new BN((fees as any).protocolShare),
    totalShare: new BN((fees as any).totalShare),
  },
  postGraduationLpPolicy: env("RAYDIUM_POST_GRADUATION_LP_POLICY", "burn") as any,
  buyAmount: new BN(env("RAYDIUM_INITIAL_BUY_AMOUNT_RAW", "0")),
  createOnly: envBool("RAYDIUM_CREATE_ONLY", true),
  extraSigners: [mintA],
  txVersion: TxVersion.V0,
  slippage: new BN(env("SLIPPAGE_BPS", "100")),
} as any);
const { execute, extInfo } = launch;

printJson({
  programId,
  configId,
  mint: mintA.publicKey,
  owner: owner.publicKey,
  extInfo,
  dryRun: !envBool("SEND_TRANSACTION"),
});

const feeLamports = await estimateAndPrintTransactionCost((launch as any).transactions ?? (launch as any).transaction, owner);

if (!envBool("SEND_TRANSACTION")) {
  console.log("DRY RUN: no transaction was broadcast.");
  process.exit(0);
}

await requireTransactionConfirmation(feeLamports);
const sentInfo = await execute({ sequentially: true, sendAndConfirm: true } as any);
printJson(sentInfo);
