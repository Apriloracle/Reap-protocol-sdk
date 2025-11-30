import { ethers } from "ethers";
import axios, { AxiosRequestConfig } from "axios";

const HOLOCRON_ROUTER_ADDRESS = "0x2cEC5Bf3a0D3fEe4E13e8f2267176BdD579F4fd8";

const NETWORKS: Record<string, string> = {
  "BASE": "https://sepolia.base.org",
  "AVAX": "https://api.avax-test.network/ext/bc/C/rpc",
  "CELO": "https://forno.celo-sepolia.celo-testnet.org"
};


const HOLOCRON_ABI = [
  "function checkExistence(uint256 _c) view returns (bool)",
  "function stock(uint256 _c) external"
];

export class ReapClient {
  private wallet: ethers.Wallet;
  private builderUrl: string;
  private provider: ethers.JsonRpcProvider;
  private holocron: ethers.Contract;
  private chainId: number = 43113;

  constructor(
    privateKey: string, 
    chainRpc: string = "https://avalanche-fuji.drpc.org", 
    builderUrl: string = "https://avax2.api.reap.deals"
  ) {
    this.provider = new ethers.JsonRpcProvider(chainRpc);
    this.wallet = new ethers.Wallet(privateKey, this.provider);
    this.builderUrl = builderUrl.replace(/\/$/, ""); 
    
    // Initialize Holocron Contract
    this.holocron = new ethers.Contract(HOLOCRON_ROUTER_ADDRESS, HOLOCRON_ABI, this.wallet);
    
    this.init();
  }

  private async init() {
    const net = await this.provider.getNetwork();
    this.chainId = Number(net.chainId);
    console.log(`🤖 Reap Agent Online: ${this.wallet.address} (Chain: ${this.chainId})`);
  }

  /**
   * Execute Transactions with Nonce & Gas Fixes
   */
  private async executeTransactions(txList: any[]) {
    let lastReceipt;
    
    // FIX 1: Use pending nonce
    let currentNonce = await this.provider.getTransactionCount(this.wallet.address, "pending");
    
    // FIX 2: Gas Price Buffer (1.1x)
    const feeData = await this.provider.getFeeData();
    const gasPrice = feeData.gasPrice ? (feeData.gasPrice * 110n) / 100n : undefined;

    for (const txData of txList) {
      const label = txData.label || "Transaction";
      console.log(`   📝 Signing: ${label}...`);

      const tx = {
        to: txData.to,
        data: txData.data,
        value: BigInt(txData.value),
        gasLimit: 500000,
        nonce: currentNonce,
        chainId: this.chainId,
        gasPrice: gasPrice // Apply buffered gas price
      };

      try {
        const response = await this.wallet.sendTransaction(tx);
        console.log(`   🚀 Broadcasting: ${response.hash}`);
        
        const receipt = await response.wait();
        
        if (receipt && receipt.status === 0) {
            throw new Error(`Transaction Reverted! Hash: ${receipt.hash}`);
        }

        console.log(`   ✅ Settled on-chain.`);
        lastReceipt = receipt;
        currentNonce++;

      } catch (e: any) {
        console.error(`   ❌ Tx Failed: ${e.message}`);
        if (label.includes("Approve") || label.includes("Payment")) throw e;
      }
    }
    return lastReceipt;
  }

  private async callBuilder(endpoint: string, payload: any) {
    try {
        // Inject Chain ID
        payload.chain_id = this.chainId;
        const { data } = await axios.post(`${this.builderUrl}${endpoint}`, payload);
        return data;
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.message;
      throw new Error(`Reap Protocol Error: ${msg}`);
    }
  }

  // --- SMART AVAILABILITY (Holocron Only) ---

  async checkHolocron(coordinate: string) {
    console.log(`🔎 Scanning Holocron for ${coordinate}...`);
    
    let exists = false;
    try {
        exists = await this.holocron.checkExistence(BigInt(coordinate));
    } catch (e) { exists = false; }

    console.log(`   • Holocron Index: ${exists ? '✅ FOUND' : '❌ EMPTY'}`);
    return exists;
  }

  private async indexToHolocron(coordinate: string) {
    console.log(`   📝 Indexing Coordinate ${coordinate} to Holocron...`);
    
    // Re-fetch nonce/gas
    const nonce = await this.provider.getTransactionCount(this.wallet.address, "pending");
    const feeData = await this.provider.getFeeData();
    const gasPrice = feeData.gasPrice ? (feeData.gasPrice * 110n) / 100n : undefined;

    const tx = await this.holocron.stock(BigInt(coordinate), {
        gasLimit: 150000,
        nonce,
        gasPrice
    });
    
    console.log(`   🚀 Broadcast Holocron TX: ${tx.hash}`);
    await tx.wait();
    console.log("   ✅ Index Updated.");
    
    // Small sleep to let RPC sync
    await new Promise(r => setTimeout(r, 2000));
  }

// --- src/index.ts ---

  async smartSync(item: any, transaction: any) {
    const coordinate = item.id;
    
    // 1. Check Status
    const onHolocron = await this.checkHolocron(coordinate);

    if (onHolocron) {
        console.log("⚡️ Fast Path: Item is indexed. Skipping registration.");
        return;
    }

    console.log("\n🐢 Syncing to Chain (Full Path)...");

    // 2. Register Data (if transaction exists)
    if (transaction) {
        console.log("   🔸 Registering Data on-chain...");
        
        // ⚠️ THE FIX: Wrap the single 'transaction' object in brackets [ ] 
        // to make it a list, because executeTransactions expects a list.
        await this.executeTransactions([transaction]);
        
    } else {
        console.log("   ⚠️ No registration transaction provided. Skipping to index.");
    }

    // 3. Index on Holocron
    await this.indexToHolocron(coordinate);
  }

  // --- PUBLIC API ---

  async registerIdentity(profileUri: string = "ipfs://default") {
    console.log("🆔 Registering Protocol Identity...");
    const res = await this.callBuilder("/build/identity/register", { 
        user_address: this.wallet.address,
        profile_uri: profileUri 
    });

    if (res.status === "already_registered") {
        console.log(`   ✅ Already Registered (Agent #${res.agent_id}). Skipping.`);
        return null;
    }
    return this.executeTransactions(res.transactions);
  }

  async stockShelf(productQuery: string, dryRun: boolean = false) {
    console.log(`📦 Stocking Shelf: '${productQuery}' (Dry Run: ${dryRun})`);
    
    const res = await this.callBuilder("/build/inventory/stock", {
      product_query: productQuery,
      provider_address: this.wallet.address
    });

    const items = res.meta?.items || [];
    const transactions = res.transactions || [];

    if (res.status === "payment_required") {
        console.log("🛑 402 Payment Required.");
        if (dryRun) return { receipt: null, items: [] };
        const receipt = await this.executeTransactions(transactions);
        return { receipt, items: [] };
    }

    if (dryRun) {
        console.log(`   👀 Preview: Found ${items.length} items. Cached ${transactions.length} TXs.`);
        return { receipt: null, items, transactions };
    }

    const receipt = await this.executeTransactions(transactions);
    return { receipt, items };
  }

  async buyProduct(productId: string) {
    console.log(`💸 Initiating Agentic Cart (Single Item): ${productId}`);
    const res = await this.callBuilder("/build/commerce/batch", {
      product_ids: [productId]
    });
    return this.executeTransactions(res.transactions);
  }

  async buyCart(productIds: string[]) {
    console.log(`🛒 Initiating Agentic Cart (Batch): ${productIds.length} items`);
    const res = await this.callBuilder("/build/commerce/batch", {
      product_ids: productIds
    });
    return this.executeTransactions(res.transactions);
  }
}
