The official typescript SDK for the **Reap Protocol**: The Agentic Commerce Grid.  
The Reap Protocol enables AI Agents to search for products, register them on-chain, and execute purchases.



📦 Installation

npm install @reap-protocol/sdk ethers axios



🚀 Quick Start

1. Setup
If using TypeScript, ensure your tsconfig.json targets ES2020 or higher.

2. The Agent Code

TypeScript
import { ReapClient } from "@reap-protocol/sdk";

// Use a Base Sepolia Wallet
const PRIVATE_KEY = process.env.MY_WALLET_KEY || "";

async function main() {
  // 1. Initialize
  const client = new ReapClient(PRIVATE_KEY);
  console.log("🤖 Agent Online");

  try {
    // 2. Identity
    // Ensures this wallet is registered to trade
    await client.registerIdentity();

    // 3. Discovery (Stocking)
    // Fetches data, registers it on Base Sepolia, and returns the list
    console.log("📦 Stocking Shelf...");
    const result = await client.stockShelf("Tonnino Tuna");
    
    const inventory = result.items;
    console.log(`   🔍 Found ${inventory.length} items.`);

    if (inventory.length > 0) {
        // 4. Decision Engine
        const target = inventory[0];
        console.log(`   🎯 Target: ${target.name} ($${target.price})`);

        // 5. Settlement (Agentic Cart)
        // Automatically approves USDC and executes the purchase
        console.log("💸 Purchasing...");
        const receipt = await client.buyProduct(target.id);
        
        console.log(`🎉 SUCCESS! Tx: ${receipt.hash}`);
    }

  } catch (e: any) {
    console.error("❌ Error:", e.message);
  }
}

main();



✨ Features
Typed Interfaces: Full TypeScript support for Product Data and Transactions.
Agentic Cart: Automatically routes purchases through the Protocol's batch processor.
Protocol Negotiation: Built-in support for HTTP 402 Payment Negotiation loops.
Gas Optimized: Checks on-chain state before sending registration transactions.


🔧 Configuration
code
TypeScript
const client = new ReapClient(
  "YOUR_PRIVATE_KEY",
  "https://sepolia.base.org", // Custom RPC
  "https://api.reap.deals"    // Middleware URL
);



License
MIT
