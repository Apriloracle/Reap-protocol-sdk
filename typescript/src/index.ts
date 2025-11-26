import { ethers } from "ethers";
import axios, { AxiosRequestConfig } from "axios";

export class ReapClient {
  private wallet: ethers.Wallet;
  private builderUrl: string;
  private provider: ethers.JsonRpcProvider;

  constructor(
    privateKey: string, 
    chainRpc: string = "https://avalanche-fuji.drpc.org", 
    builderUrl: string = "https://api.reap.deals"
  ) {
    this.provider = new ethers.JsonRpcProvider(chainRpc);
    this.wallet = new ethers.Wallet(privateKey, this.provider);
    this.builderUrl = builderUrl.replace(/\/$/, ""); // Remove trailing slash
    console.log(`🤖 Reap Agent Online: ${this.wallet.address}`);
  }

  /**
   * Core Logic: Signs and Broadcasts transactions sequentially.
   * Uses manual nonce management to prevent RPC lag errors.
   */
  private async executeTransactions(txList: any[]) {
    let lastReceipt;
    
    // 1. Fetch Nonce ONCE
    let currentNonce = await this.provider.getTransactionCount(this.wallet.address, "pending");

    for (const txData of txList) {
      const label = txData.label || "Transaction";
      console.log(`   📝 Signing: ${label}...`);

      const tx = {
        to: txData.to,
        data: txData.data,
        value: BigInt(txData.value),
        gasLimit: 500000, // Safety limit
        nonce: currentNonce,
        chainId: (await this.provider.getNetwork()).chainId
      };

      try {
        // 2. Sign & Send
        const response = await this.wallet.sendTransaction(tx);
        console.log(`   🚀 Broadcasting: ${response.hash}`);
        
        // 3. Wait
        const receipt = await response.wait();
        
        // 4. Check Status (1 = Success, 0 = Revert)
        if (receipt && receipt.status === 0) {
            throw new Error(`Transaction Reverted! Hash: ${receipt.hash}`);
        }

        console.log(`   ✅ Settled on-chain.`);
        lastReceipt = receipt;
        
        // 5. Increment Nonce
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
      const { data } = await axios.post(`${this.builderUrl}${endpoint}`, payload);
      return data;
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.message;
      throw new Error(`Reap Protocol Error: ${msg}`);
    }
  }

  // --- PUBLIC API ---

  async getProduct(productId: string) {
    const safeId = encodeURIComponent(productId);
    const { data } = await axios.get(`${this.builderUrl}/read/product/${safeId}`);
    return data;
  }

 // ... inside ReapClient class ...

  async registerIdentity(profileUri: string = "ipfs://default") {
    console.log("🆔 Registering Protocol Identity...");
    const res = await this.callBuilder("/build/identity/register", { 
        user_address: this.wallet.address,
        profile_uri: profileUri 
    });

    if (res.status === "already_registered") {
        console.log(`   ✅ Already Registered (Agent #${res.agent_id}). Skipping transaction.`);
        return null;
    }

    return this.executeTransactions(res.transactions);
  }

async stockShelf(productQuery: string) {
    console.log(`📦 Stocking Shelf: '${productQuery}'`);
    const res = await this.callBuilder("/build/inventory/stock", {
      product_query: productQuery,
      provider_address: this.wallet.address
    });

    if (res.status === "payment_required") {
        console.log("🛑 402 Payment Required via JSON Spec.");
        console.log(`   🧾 Invoice: ${res.meta.description}`);
    } else {
        console.log(`   🔍 Found ${res.meta.count || 0} items.`);
    }

    const receipt = await this.executeTransactions(res.transactions);

    // --- THE FIX: Return both Receipt AND Items ---
    return {
        receipt,
        items: res.meta?.items || []
    };
    // ----------------------------------------------
  }

  async buyProduct(productId: string) {
    console.log(`💸 Initiating Agentic Cart (Single Item): ${productId}`);
    // Route to batch endpoint
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

  async fetch(url: string, config: AxiosRequestConfig = {}) {
    console.log(`🌍 Accessing ${url}...`);
    try {
      return await axios.get(url, config);
    } catch (error: any) {
      if (error.response && error.response.status === 402) {
        console.log("🛑 x402 Payment Required. Engaging Protocol...");
        const header = error.response.headers["www-authenticate"];

        if (header && header.includes("X402")) {
            const match = header.match(/resource_id="([^"]+)"/);
            if (match && match[1]) {
                const rid = match[1];
                
                // Pay Protocol
                const receipt = await this.buyProduct(rid);
                
                if (!receipt) throw new Error("Payment Transaction failed");
                const proof = receipt.hash;
                
                console.log(`   🔄 Submitting Proof for Reactive Release: ${proof}`);

                // Release Data
                const newConfig = { ...config, headers: { ...config.headers, "Authorization": `X402-Proof ${proof}` } };
                return await axios.get(url, newConfig);
            }
        }
      }
      throw error;
    }
  }
}
