# Reap Protocol SDK

**The official Python SDK for the Reap Protocol: The Agentic Commerce Grid.**

The Reap Protocol enables AI Agents to search for products, register them on-chain (Base Sepolia), and execute atomic purchases without needing to understand smart contract ABIs.

## 📦 Installation

```bash
pip install reap-protocol
```

## 🚀 Quick Start

This example demonstrates the full Agentic Commerce Loop: Identity -> Discovery -> Settlement.

```python
import os
from reap_protocol.client import ReapClient

# 1. Configuration
# Use a Base Sepolia Wallet with ETH (for gas) and USDC (for purchases)
PRIVATE_KEY = os.getenv("MY_WALLET_KEY") 

def main():
    # Initialize the Agent (Points to official middleware by default)
    client = ReapClient(private_key=PRIVATE_KEY)

    # 2. Identity (One-time setup)
    # Registers your wallet as an authorized Agent on the Protocol
    print("🆔 Checking Identity...")
    client.register_identity()

    # 3. JIT Stocking (Discovery)
    # Searches Web2 (Reap Deals), registers items on-chain, and returns inventory
    print("📦 Stocking Shelf with 'Gaming Laptop'...")
    result = client.stock_shelf("Gaming Laptop")
    
    inventory = result.get('items', [])
    print(f"   🔍 Found {len(inventory)} items on-chain.")

    if not inventory:
        return

    # 4. Decision Logic
    # Example: Pick the first available item
    target_item = inventory[0]
    print(f"   🎯 Selected: {target_item['name']} (${target_item['price']})")
    print(f"      ID: {target_item['id']}")

    # 5. Agentic Cart (Settlement)
    # Handles ERC20 Approvals and Atomic Purchase in one flow
    print(f"💸 Buying Item...")
    receipt = client.buy_product(target_item['id'])
    
    if receipt:
        print(f"🎉 SUCCESS! Transaction Hash: {receipt['transactionHash'].hex()}")

if __name__ == "__main__":
    main()
```

## 🛠 Configuration

You can override defaults for custom RPCs or self-hosted middleware.

```python
client = ReapClient(
    private_key="...",
    chain_rpc="https://base-sepolia.g.alchemy.com/v2/YOUR_KEY", # Faster RPC
    builder_url="https://avax.api.reap.deals" # Official Middleware
)
```

## ✨ Features

* **Agentic Cart**: Routes single or multiple items through a batch processor, optimizing gas and handling USDC approvals automatically.
* **JIT Stocking**: "Just-In-Time" inventory system. If an agent searches for an item not yet on the blockchain, the Protocol indexes it in real-time.
* **Self-Custody**: Your private key never leaves your local machine. The SDK signs transactions locally.
* **Smart Updates**: The Middleware checks on-chain state to prevent redundant transactions.

## License

MIT
