# @reap-protocol/sdk

**The official TypeScript/Node.js SDK for the Reap Protocol: The Agentic Commerce Grid.**

The Reap Protocol enables AI Agents to search for products, register them on-chain, and execute atomic purchases without needing to understand smart contract ABIs. It acts as the bridge between Web2 products data and Web3 commerce settlement.

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

// Optional: Use a specific RPC (e.g., Base Sepolia or Avalanche Fuji)
const CHAIN_RPC = "https://api.avax-test.network/ext/bc/C/rpc"; 

async function main() {
  // 1. Initialize the Agent
  const client = new ReapClient(PRIVATE_KEY, CHAIN_RPC);
  
  // Wait for Chain ID initialization
  await new Promise(r => setTimeout(r, 1000));
  console.log("🤖 Agent Online");

  try {
    // 2. Identity (One-time setup)
    // Registers your wallet as an authorized Agent on the Protocol
    console.log("🆔 Checking Identity...");
    await client.registerIdentity();

    // 3. Discovery (Dry Run Mode)
    // Pass 'true' to get the items AND the transactions without executing them yet.
    console.log("📦 Browsing for 'Gaming Laptop'...");
    
    // dryRun = true
    const result = await client.stockShelf("Gaming Laptop", true); 
    
    const inventory = result.items || [];
    const transactions = result.transactions || [];

    console.log(`   🔍 Found ${inventory.length} items.`);

    if (inventory.length > 0) {
        // 4. Decision Logic
        // Pick the first item and its corresponding registration transaction
        const targetItem = inventory[0];
        const targetTx = transactions[0]; 

        console.log(`   🎯 Selected: ${targetItem.name} ($${targetItem.price})`);

        // 5. Smart Sync (The "Gas Saver")
        // Checks the Holocron (Index) first. 
        // If the item exists, it skips registration. 
        // If not, it executes the targetTx and indexes it.
        await client.smartSync(targetItem, targetTx);

        // 6. Agentic Cart (Settlement)
        // Automatically approves USDC and executes the atomic purchase
        console.log("💸 Buying Item...");
        const receipt = await client.buyProduct(targetItem.id);
        
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

## 🕵️ Agent Discovery (New)

You can now search for other AI Agents (MCP, x402, A2A).

```typescript
// 1. Search for Agents
// Registries: 'mcp' (AI Models), 'x402' (Payment Agents), 'a2a' (Autonomous)
const agents = await client.searchAgents("ecommerce", "x402");

if (agents.length > 0) {
    const targetAgent = agents[0];
    console.log(`Found: ${targetAgent.name}`);
}
```

## 🔧 Configuration

You can override defaults for custom RPCs or self-hosted middleware.
```typescript
const client = new ReapClient(
  "YOUR_PRIVATE_KEY",
  "https://avax-fuji.g.alchemy.com/v2/YOUR_KEY", // Custom RPC
  "https://avax2.api.reap.deals"    // Middleware URL
);
```

## ✨ Features

* **Agent Discovery**: Search thousands of AI Agents from MCP, x402, and A2A registries.
* **JIT Stocking**: "Just-In-Time" inventory system. If an agent searches for an item not yet on the blockchain, the Protocol indexes it in real-time.
* **Agentic Cart**: Automatically routes purchases through the Protocol's batch processor.
* **Protocol Negotiation**: Built-in support for HTTP 402 Payment Negotiation loops.

## License

MIT
