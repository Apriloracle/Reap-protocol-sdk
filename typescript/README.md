# @reap-protocol/sdk

**The official TypeScript/Node.js SDK for the Reap Protocol: The Agentic Commerce Grid.**

The Reap Protocol enables AI Agents to search for products, register them on-chain (Base Sepolia), and execute atomic purchases without needing to understand smart contract ABIs. It acts as the bridge between Web2 data availability and Web3 settlement logic.

## 📦 Installation
```bash
npm install @reap-protocol/sdk ethers axios
```

## 🚀 Quick Start

This example demonstrates the full Agentic Commerce Loop: Identity -> Discovery -> Settlement.

### 1. Setup

If using TypeScript, ensure your tsconfig.json targets ES2020 or higher.

### 2. The Agent Code (agent.ts)
```typescript
import { ReapClient } from "@reap-protocol/sdk";

// Load your private key securely
const PRIVATE_KEY = process.env.MY_WALLET_KEY || "";

async function main() {
  // 1. Initialize the Agent
  // (Points to official middleware by default)
  const client = new ReapClient(PRIVATE_KEY);
  console.log("🤖 Agent Online");

  try {
    // 2. Identity (One-time setup)
    // Registers your wallet as an authorized Agent on the Protocol
    console.log("🆔 Checking Identity...");
    await client.registerIdentity();

    // 3. JIT Stocking (Discovery)
    // Searches Web2 (Reap Deals), registers items on-chain, and returns inventory
    console.log("📦 Stocking Shelf with 'Gaming Laptop'...");
    const result = await client.stockShelf("Gaming Laptop");
    
    const inventory = result.items;
    console.log(`   🔍 Found ${inventory.length} items on-chain.`);

    if (inventory.length > 0) {
        // 4. Decision Logic
        // Example: Pick the first available item
        const target = inventory[0];
        console.log(`   🎯 Selected: ${target.name} ($${target.price})`);
        console.log(`      ID: ${target.id}`);

        // 5. Agentic Cart (Settlement)
        // Automatically approves USDC and executes the atomic purchase
        console.log("💸 Buying Item...");
        const receipt = await client.buyProduct(target.id);
        
        if (receipt) {
            console.log(`🎉 SUCCESS! Transaction Hash: ${receipt.hash}`);
        }
    } else {
        console.log("❌ No items found.");
    }

  } catch (e: any) {
    console.error("❌ Error:", e.message);
  }
}

main();
```

### 3. Run It
```bash
# Install execution tools if you haven't already
npm install --save-dev ts-node typescript @types/node

# Run
npx ts-node agent.ts
```

## 🔧 Configuration

You can override defaults for custom RPCs or self-hosted middleware.
```typescript
const client = new ReapClient(
  "YOUR_PRIVATE_KEY",
  "https://base-sepolia.g.alchemy.com/v2/YOUR_KEY", // Custom RPC
  "https://api.reap.deals"    // Middleware URL
);
```

## ✨ Features

* **JIT Stocking**: "Just-In-Time" inventory system. If an agent searches for an item not yet on the blockchain, the Protocol indexes it in real-time.
* **Agentic Cart**: Automatically routes purchases through the Protocol's batch processor.
* **Protocol Negotiation**: Built-in support for HTTP 402 Payment Negotiation loops.
* **Gas Optimized**: Checks on-chain state before sending registration transactions.

## License

MIT
