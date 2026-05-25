import bs58 from "bs58";
import { createKeyPairSignerFromBytes, createSolanaRpc, address, devnet, mainnet } from "@solana/kit";
import { setRpc, swap, swapInstructions, WhirlpoolDeployment } from "@orca-so/whirlpools";
import { env, envBool, printJson, requireTransactionConfirmation } from "./common.js";

const rpcUrl = env("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com");
const cluster = env("SOLANA_CLUSTER", "mainnet-beta");
const rpc = createSolanaRpc(cluster === "devnet" ? devnet(rpcUrl) : mainnet(rpcUrl));
const wallet = await createKeyPairSignerFromBytes(bs58.decode(env("SOLANA_ACTIVE_PRIVATE_KEY_BASE58", undefined, true)));
const whirlpoolAddress = address(env("ORCA_WHIRLPOOL_ADDRESS", undefined, true));
const mintAddress = address(env("INPUT_MINT", undefined, true));
const amount = BigInt(env("RAW_AMOUNT", undefined, true));
const slippageBps = Number(env("SLIPPAGE_BPS", "100"));
const deployment = cluster === "devnet" ? WhirlpoolDeployment.devnet : WhirlpoolDeployment.mainnet;

setRpc(rpcUrl);

const { quote, instructions } = await swapInstructions(
  rpc,
  { inputAmount: amount, mint: mintAddress },
  whirlpoolAddress,
  {
    slippageToleranceBps: slippageBps,
    signer: wallet,
    whirlpoolDeployment: deployment,
  },
);

printJson({
  whirlpool: whirlpoolAddress,
  inputMint: mintAddress,
  inputAmount: amount,
  estimatedOut: (quote as any).tokenEstOut ?? quote,
  minimumOut: (quote as any).tokenMinOut,
  instructionCount: instructions.length,
  dryRun: !envBool("SEND_TRANSACTION"),
});
console.log("Estimated network fee: unavailable until Orca builds the final transaction internally.");
console.log("Review quote output above. Estimate excludes token amounts, rent deposits, DEX/platform fees, and priority-fee changes.");

if (!envBool("SEND_TRANSACTION")) {
  console.log("DRY RUN: no transaction was broadcast.");
  process.exit(0);
}

await requireTransactionConfirmation(null);
const signature = await swap(
  { inputAmount: amount, mint: mintAddress },
  whirlpoolAddress,
  {
    slippageToleranceBps: slippageBps,
    signer: wallet,
    whirlpoolDeployment: deployment,
  },
).then((action) => action.callback(wallet));
printJson({ signature });
