import requests
import time
from web3 import Web3

# --- COMPATIBILITY FIX: MIDDLEWARE (V6 vs V7) ---
try:
    from web3.middleware import ExtraDataToPOAMiddleware
    POAMiddleware = ExtraDataToPOAMiddleware
except ImportError:
    from web3.middleware import geth_poa_middleware
    POAMiddleware = geth_poa_middleware
# ------------------------------------------------

class ReapClient:
    def __init__(self, private_key, chain_rpc="https://sepolia.base.org", builder_url="https://api.reap.deals"):
        """
        Initialize the Reap Protocol Agent.
        """
        self.builder_url = builder_url.rstrip('/') # Remove trailing slash if present
        
        # Web3 Setup
        self.w3 = Web3(Web3.HTTPProvider(chain_rpc))
        self.w3.middleware_onion.inject(POAMiddleware, layer=0)
        self.account = self.w3.eth.account.from_key(private_key)
        
        print(f"🤖 Reap Agent Online: {self.account.address}")

    def _execute_transactions(self, tx_list):
        receipts = []
        
        # 1. Fetch Nonce ONCE at the start
        current_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
        
        for i, tx_data in enumerate(tx_list):
            label = tx_data.get('label', f'Tx {i+1}')
            print(f"   📝 Signing: {label}...")
            
            # 2. Construct Tx
            tx = {
                'to': tx_data['to'],
                'data': tx_data['data'],
                'value': int(tx_data['value']),
                'gas': 500000, 
                'gasPrice': self.w3.eth.gas_price,
                'nonce': current_nonce,
                'chainId': self.w3.eth.chain_id
            }

            # 3. Sign
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            
            # --- COMPATIBILITY FIX: ATTRIBUTES (V6 vs V7) ---
            try:
                raw_tx = signed.raw_transaction
            except AttributeError:
                raw_tx = signed.rawTransaction
            # ------------------------------------------------

            # 4. Broadcast & Wait
            try:
                tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                print(f"   🚀 Broadcasting: {tx_hash.hex()}")
                
                # 5. Wait for Settlement
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                # --- CRITICAL STATUS CHECK ---
                if receipt['status'] == 0:
                    raise Exception(f"Transaction Reverted on-chain! Hash: {tx_hash.hex()}")
                # -----------------------------

                receipts.append(receipt)
                print("   ✅ Settled on-chain.")
                
                # 6. Increment Nonce Safely
                current_nonce += 1
                
            except Exception as e:
                print(f"   ❌ Tx Failed: {e}")
                # If it's a payment/approval failure, stop. If stocking, continue.
                if "Pay" in label or "Approve" in label:
                    raise e
                continue
            
        return receipts[-1] if receipts else None

    def _call_builder(self, endpoint, payload):
        res = requests.post(f"{self.builder_url}{endpoint}", json=payload)
        if res.status_code != 200:
            # Try to extract detail message
            try:
                err_msg = res.json().get('detail', res.text)
            except:
                err_msg = res.text
            raise Exception(f"Reap Protocol Error: {err_msg}")
        return res.json()

    # --- PUBLIC API ---

    def get_product(self, product_id):
        """Read-Only Check from Blockchain"""
        import urllib.parse
        safe_id = urllib.parse.quote(str(product_id))
        res = requests.get(f"{self.builder_url}/read/product/{safe_id}")
        return res.json()

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

    def stock_shelf(self, product_query):
        print(f"📦 Stocking Shelf: '{product_query}'")
        res = self._call_builder("/build/inventory/stock", {
            "product_query": product_query,
            "provider_address": self.account.address
        })
        
        # Handle x402 Negotiation (Payment Required)
        if res.get("status") == "payment_required":
            print("🛑 402 Payment Required via JSON Spec.")
            print(f"   🧾 Invoice: {res['meta']['description']}")
            receipt = self._execute_transactions(res['transactions'])
            return {"receipt": receipt, "items": []}
            
        # Handle 200 OK (Bulk Stocking)
        receipt = self._execute_transactions(res['transactions'])
        
        # RETURN DATA (Matches TS behavior)
        return {
            "receipt": receipt,
            "items": res.get("meta", {}).get("items", [])
        }

    def buy_product(self, product_id):
        print(f"💸 Initiating Agentic Cart (Single Item): {product_id}")
        # ROUTE TO BATCH ENDPOINT (Same as TS SDK)
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

    def fetch(self, url, method="GET", json=None, headers={}):
        """Handles HTTP 402 Negotiation & Reactive Release"""
        print(f"🌍 Accessing {url}...")
        response = requests.request(method, url, json=json, headers=headers)

        if response.status_code == 402:
            print("🛑 x402 Payment Required. Engaging Protocol...")
            auth_header = response.headers.get("WWW-Authenticate", "")
            
            if 'resource_id="' in auth_header:
                start = auth_header.find('resource_id="') + 13
                end = auth_header.find('"', start)
                rid = auth_header[start:end]
                
                # Pay Protocol
                receipt = self.buy_product(rid)
                proof = receipt['transactionHash'].hex()
                
                # Release Data
                print(f"   🔄 Submitting Proof for Reactive Release: {proof}")
                headers['Authorization'] = f"X402-Proof {proof}"
                return requests.request(method, url, json=json, headers=headers)
        
        return response