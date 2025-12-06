# Reap Protocol SDK

**The official Python SDK for the Reap Protocol: The Agentic Commerce Grid.**

The Reap Protocol enables AI Agents to search for products, register them on-chain, and execute atomic purchases without needing to understand smart contract ABIs.

## 📦 Installation

```bash
pip install reap-protocol
```

## 🚀 Quick Start

This example demonstrates the full Agentic Commerce Loop: Identity -> Discovery -> Smart Sync -> Settlement.

```python
import os
import time
from reap_protocol.client import ReapClient

# 1. Configuration
# Use a funded testnet wallet (AVAX Fuji, Celo Alfajores, or Base Sepolia)
PRIVATE_KEY = os.getenv("MY_WALLET_KEY") 
CHAIN_RPC = "https://api.avax-test.network/ext/bc/C/rpc" # Example: Avalanche Fuji

def main():
    # Initialize the Agent
    client = ReapClient(
        private_key=PRIVATE_KEY,
        chain_rpc=CHAIN_RPC
    )
    
    # Wait for connection
    time.sleep(1)
    print(f"🤖 Agent Online: {client.account.address}")

    # 2. Identity (One-time setup)
    # Registers your wallet as an authorized Agent on the Protocol
    print("🆔 Checking Identity...")
    client.register_identity()

    # 3. Discovery (Dry Run Mode)
    # Searches Web2 (Reap Deals). We use dry_run=True to get the data
    # without executing the registration transactions immediately.
    print("📦 Browsing for 'Gaming Laptop'...")
    
    result = client.stock_shelf("Gaming Laptop", dry_run=True)
    
    items = result.get('items', [])
    transactions = result.get('transactions', [])
    
    print(f"   🔍 Found {len(items)} items.")

    if not items:
        print("❌ No items found.")
        return

    # 4. Decision Logic
    # Example: Pick the first available item
    target_item = items[0]
    
    # The API returns transactions in the same order as items.
    # We grab the specific registration TX for this item.
    target_tx = transactions[0] 

    print(f"   🎯 Selected: {target_item['name']} (${target_item['price']})")
    print(f"      ID: {target_item['id']}")

    # 5. Smart Sync 
    # The SDK checks if item is stocked.
    # - If found: It skips registration (Zero Gas).
    # - If missing: It runs the registration TX and updates the index.
    print("🧠 Running Smart Sync...")
    client.smart_sync(target_item, [target_tx])

    # 6. Agentic Cart (Settlement)
    # Handles ERC20 Approvals and Atomic Purchase in one flow
    print(f"💸 Buying Item...")
    receipt = client.buy_product(target_item['id'])
    
    if receipt:
        print(f"🎉 SUCCESS! Transaction Hash: {receipt['transactionHash'].hex()}")

if __name__ == "__main__":
    main()
```

## 🕵️ Agent Discovery (New)

You can now search for other AI Agents (MCP, x402, A2A).

```python
# 1. Search for Agents
# Registries: 'mcp', 'x402', 'a2a'
agents = client.search_agents("ecommerce", registry="x402")

if agents:
    target_agent = agents[0]
    print(f"Found: {target_agent.get('name')}")

```

## 🛠 Configuration

You can override defaults for custom RPCs or self-hosted middleware.

```python
client = ReapClient(
    private_key="...",
    chain_rpc="https://avax-fuji.g.alchemy.com/v2/YOUR_KEY", # Faster RPC
    builder_url="https://avax2.api.reap.deals" # Official Middleware
)
```

## ✨ Features

* **Agent Discovery**: Search thousands of AI Agents from MCP, x402, and A2A registries.
* **Agentic Cart**: Routes single or multiple items through a batch processor, optimizing gas and handling USDC approvals automatically.
* **JIT Stocking**: "Just-In-Time" inventory system. If an agent searches for an item not yet on the blockchain, the Protocol indexes it in real-time.
* **Smart Updates**: The Middleware checks on-chain state to prevent redundant transactions.

## License

MIT
