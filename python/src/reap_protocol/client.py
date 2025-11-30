import requests
import time
import json
import urllib.parse
from web3 import Web3

# --- COMPATIBILITY FIX: MIDDLEWARE (V6 vs V7) ---
try:
    from web3.middleware import ExtraDataToPOAMiddleware
    POAMiddleware = ExtraDataToPOAMiddleware
except ImportError:
    from web3.middleware import geth_poa_middleware
    POAMiddleware = geth_poa_middleware
# ------------------------------------------------

# --- CONSTANTS & ABIS ---
HOLOCRON_ROUTER_ADDRESS = "0x2cEC5Bf3a0D3fEe4E13e8f2267176BdD579F4fd8"

HOLOCRON_ABI = [
    {"inputs": [{"name": "_c", "type": "uint256"}], "name": "checkExistence", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "_c", "type": "uint256"}], "name": "stock", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]
    # Chains to scan
SCAN_NETWORKS = {
        "BASE": "https://sepolia.base.org",
        "AVAX": "https://api.avax-test.network/ext/bc/C/rpc",
        "CELO": "https://forno.celo-sepolia.celo-testnet.org"
    }


class ReapClient:
    def __init__(self, private_key, chain_rpc="https://avalanche-fuji.drpc.org", builder_url="https://avax2.api.reap.deals"):
        """
        Initialize the Reap Protocol Agent.
        """
        self.builder_url = builder_url.rstrip('/') 
        
        # Web3 Setup
        self.w3 = Web3(Web3.HTTPProvider(chain_rpc))
        self.w3.middleware_onion.inject(POAMiddleware, layer=0)
        self.account = self.w3.eth.account.from_key(private_key)
        
        print("🔌 Connecting to Chain...")
        try:
            self.chain_id = self.w3.eth.chain_id
        except Exception as e:
            print(f"⚠️ Warning: Could not fetch Chain ID on startup: {e}")
            self.chain_id = 43113 # Default fallback

        print(f"🤖 Reap Agent Online: {self.account.address} (Chain ID: {self.chain_id})")

        # Initialize Holocron Contract
        self.holocron = self.w3.eth.contract(address=HOLOCRON_ROUTER_ADDRESS, abi=HOLOCRON_ABI)

    def _execute_transactions(self, tx_list):
        receipts = []
        
        # 1. FIX: Use 'pending' nonce to allow rapid sequential transactions
        current_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
        
        # 2. FIX: Buffer Gas Price (1.1x) to prevent "underpriced" errors on Base
        gas_price = int(self.w3.eth.gas_price * 1.10)

        for i, tx_data in enumerate(tx_list):
            label = tx_data.get('label', f'Tx {i+1}')
            print(f"   📝 Signing: {label}...")
            
            SAFE_GAS_LIMIT = 500000 

            tx = {
                'to': tx_data['to'],
                'data': tx_data['data'],
                'value': int(tx_data['value']),
                'gas': SAFE_GAS_LIMIT,
                'gasPrice': gas_price, 
                'nonce': current_nonce,
                'chainId': self.chain_id
            }

            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            
            try:
                raw_tx = signed.raw_transaction
            except AttributeError:
                raw_tx = signed.rawTransaction

            try:
                tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                print(f"   🚀 Broadcasting: {tx_hash.hex()}")
                
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt['status'] == 0:
                    raise Exception(f"Transaction Reverted on-chain! Hash: {tx_hash.hex()}")

                receipts.append(receipt)
                print("   ✅ Settled on-chain.")
                
                current_nonce += 1
                
            except Exception as e:
                print(f"   ❌ Tx Failed: {e}")
                if "Pay" in label or "Approve" in label:
                    raise e
                continue
            
        return receipts[-1] if receipts else None

    def _call_builder(self, endpoint, payload):
        payload['chain_id'] = self.chain_id
        res = requests.post(f"{self.builder_url}{endpoint}", json=payload)
        if res.status_code != 200:
            try:
                err_msg = res.json().get('detail', res.text)
            except:
                err_msg = res.text
            raise Exception(f"Reap Protocol Error: {err_msg}")
        return res.json()

    # --- SMART AVAILABILITY CHECKS (Holocron Only) ---

    def check_holocron(self, coordinate):
        """Checks if the item is indexed in the Holocron."""
        print(f"🔎 Scanning Holocron for {coordinate}...")
        try:
            exists = self.holocron.functions.checkExistence(int(coordinate)).call()
        except:
            exists = False

        print(f"   • Holocron Index: {'✅ FOUND' if exists else '❌ EMPTY'}")
        return exists

    def _index_to_holocron(self, coordinate):
        """Internal method to update the Holocron Index."""
        print(f"   📝 Indexing Coordinate {coordinate} to Holocron...")
        
        # Re-fetch nonce/gas for this specific stand-alone op
        nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
        gas_price = int(self.w3.eth.gas_price * 1.10)

        tx = self.holocron.functions.stock(int(coordinate)).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': 150000,
            'gasPrice': gas_price,
            'chainId': self.chain_id
        })
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        print(f"   🚀 Broadcast Holocron TX: {tx_hash.hex()}")
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print("   ✅ Index Updated.")
        
        # RPC Sync buffer
        time.sleep(2)

    def smart_sync(self, item, transactions):
        """
        Intelligently syncs the item to the chain.
        1. If on Holocron -> Assume Available.
        2. If !Holocron -> Register Data (via TXs) + Index Holocron.
        """
        coordinate = item['id']
        
        on_holocron = self.check_holocron(coordinate)

        if on_holocron:
            print("⚡️ Fast Path: Item is indexed. Skipping registration.")
            return

        print("\n🐢 Syncing to Chain (Full Path)...")

        # Step A: Execute Registration Transactions (provided by API)
        print("   🔸 Registering Data on-chain...")
        self._execute_transactions(transactions)

        # Step B: Index on Holocron
        self._index_to_holocron(coordinate)

    # --- PUBLIC API ---

    def register_identity(self, profile_uri="ipfs://default"):
        print("🆔 Registering Protocol Identity...")
        res = self._call_builder("/build/identity/register", {
            "user_address": self.account.address,
            "profile_uri": profile_uri
        })
        
        if res.get("status") == "already_registered":
            print(f"   ✅ Already Registered (Agent #{res.get('agent_id')}). Skipping.")
            return None
            
        return self._execute_transactions(res['transactions'])

    def stock_shelf(self, product_query, dry_run=False):
        """
        Search for items. 
        If dry_run=True, returns items + transactions without executing them (for Smart Sync).
        """
        print(f"📦 Stocking Shelf: '{product_query}' (Dry Run: {dry_run})")
        res = self._call_builder("/build/inventory/stock", {
            "product_query": product_query,
            "provider_address": self.account.address
        })
        
        items = res.get("meta", {}).get("items", [])
        transactions = res.get("transactions", [])

        # Payment Required
        if res.get("status") == "payment_required":
            print("🛑 402 Payment Required via JSON Spec.")
            if dry_run: return {"receipt": None, "items": []}
            receipt = self._execute_transactions(transactions)
            return {"receipt": receipt, "items": []}
            
        # Success
        if dry_run:
            print(f"   👀 Preview: Found {len(items)} items. Cached {len(transactions)} TXs.")
            return {"receipt": None, "items": items, "transactions": transactions}
        
        # Execute immediately (Legacy behavior)
        receipt = self._execute_transactions(transactions)
        return {"receipt": receipt, "items": items}

    def buy_product(self, product_id):
        print(f"💸 Initiating Agentic Cart (Single Item): {product_id}")
        res = self._call_builder("/build/commerce/batch", {
            "product_ids": [product_id]
        })
        return self._execute_transactions(res['transactions'])

    def buy_cart(self, product_ids):
        print(f"🛒 Initiating Agentic Cart (Batch): {len(product_ids)} items")
        res = self._call_builder("/build/commerce/batch", {
            "product_ids": product_ids
        })
        return self._execute_transactions(res['transactions'])
