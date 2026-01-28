from web3 import Web3
from django.conf import settings
import json
import os
import threading


class BlockchainService:
    """
    Singleton service for blockchain operations.
    Maintains a single Web3 connection instance for better performance.
    """
    _instance = None
    _w3 = None
    _contract = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implement singleton pattern with thread safety"""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Web3 connection and contract (only once)"""
        if self._w3 is None:
            with self._lock:
                if self._w3 is None:
                    self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Web3 connection and load contract"""
        ganache_url = os.getenv('GANACHE_URL', 'http://127.0.0.1:7545')
        self._w3 = Web3(Web3.HTTPProvider(ganache_url))
        
        if not self._w3.is_connected():
            raise Exception(f"Failed to connect to Ganache at {ganache_url}")
        
        # Load contract
        contract_path = os.path.join(
            settings.BASE_DIR,
            'blockchain_project',
            'build',
            'contracts',
            'DocumentRegistry.json'
        )
        
        with open(contract_path) as f:
            contract_json = json.load(f)
            contract_abi = contract_json['abi']
            
        # Get contract address from settings or environment
        contract_address = getattr(settings, 'BLOCKCHAIN_CONTRACT_ADDRESS', None)
        if not contract_address:
            # Try to get from deployed networks
            network_id = str(self._w3.net.version)
            if network_id in contract_json.get('networks', {}):
                contract_address = contract_json['networks'][network_id]['address']
        
        if not contract_address:
            raise Exception("Contract address not configured")
        
        self._contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=contract_abi
        )
    
    @property
    def w3(self):
        """Get Web3 instance"""
        return self._w3
    
    @property
    def contract(self):
        """Get contract instance"""
        return self._contract
        
        if not os.path.exists(contract_path):
            raise Exception(
                "Contract not found! Did you run 'truffle migrate'?"
            )
        
        # Load contract JSON
        with open(contract_path) as f:
            contract_json = json.load(f)
            contract_abi = contract_json['abi']
            
            # Get contract address from networks
            # Network ID 5777 is Ganache default
            networks = contract_json.get('networks', {})
            network_id = str(list(networks.keys())[0]) if networks else None
            
            if not network_id or 'address' not in networks[network_id]:
                raise Exception(
                    "Contract not deployed! Run 'truffle migrate --reset'"
                )
            
            contract_address = networks[network_id]['address']
        
        # Create contract instance
        return self.w3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )
    
    def get_account_for_user(self, user_id):
        """
        Assign a Ganache account to a user
        
        WHY: Each user needs an Ethereum address to interact with blockchain
        SIMPLE APPROACH: Use user_id to select from Ganache's 10 accounts
        
        In production, users would have their own wallets (MetaMask)
        """
        # Ganache gives us 10 accounts, use user_id to pick one
        account_index = (user_id - 1) % 10
        return self.w3.eth.accounts[account_index]
    
    def register_document(self, user_id, document_id, document_hash, document_type):
        """
        Register document hash on blockchain
        
        TRANSACTION FLOW:
        1. Build transaction with contract function call
        2. Sign transaction with user's account
        3. Send to blockchain
        4. Wait for confirmation
        5. Return transaction receipt
        """
        
        # Get user's account
        user_account = self.get_account_for_user(user_id)
        
        # Build transaction
        tx = self.contract.functions.registerDocument(
            document_id,
            document_hash,
            document_type
        ).build_transaction({
            'from': user_account,
            'nonce': self.w3.eth.get_transaction_count(user_account),
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Send transaction (Ganache auto-signs for its own accounts)
        tx_hash = self.w3.eth.send_transaction(tx)
        
        # Wait for transaction to be mined
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            'transaction_hash': tx_receipt['transactionHash'].hex(),
            'block_number': tx_receipt['blockNumber'],
            'gas_used': tx_receipt['gasUsed'],
            'status': 'success' if tx_receipt['status'] == 1 else 'failed'
        }
    
    def verify_document(self, user_id, document_id, document_hash):
        """
        Verify if document hash matches what's stored on blockchain
        
        VERIFICATION PROCESS:
        1. Call smart contract's verifyDocument function
        2. Contract compares hashes
        3. Returns true/false
        """
        
        user_account = self.get_account_for_user(user_id)
        
        # Call contract function (this is a transaction that modifies state)
        tx = self.contract.functions.verifyDocument(
            document_id,
            document_hash
        ).build_transaction({
            'from': user_account,
            'nonce': self.w3.eth.get_transaction_count(user_account),
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self._get_private_key(user_account))
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get events from transaction to see if verification passed
        # For simplicity, we'll also do a direct call to check
        is_valid = self._check_document_hash(user_account, document_id, document_hash)
        
        return {
            'is_valid': is_valid,
            'transaction_hash': tx_receipt['transactionHash'].hex(),
            'block_number': tx_receipt['blockNumber']
        }
    
    def _check_document_hash(self, user_account, document_id, document_hash):
        """
        Helper method to check document hash without creating transaction
        """
        try:
            # Get document from blockchain
            doc = self.contract.functions.getDocument(
                user_account,
                document_id
            ).call()
            
            # doc is tuple: (documentHash, owner, timestamp, documentType, exists)
            stored_hash = doc[0]
            
            return stored_hash == document_hash
        except:
            return False
    
    def get_document(self, user_id, document_id):
        """
        Retrieve document details from blockchain
        
        READ-ONLY: This doesn't cost gas, just reads data
        """
        
        user_account = self.get_account_for_user(user_id)
        
        try:
            # Call contract function (read-only, no transaction needed)
            doc = self.contract.functions.getDocument(
                user_account,
                document_id
            ).call()
            
            # Unpack tuple
            document_hash, owner, timestamp, document_type, exists = doc
            
            if not exists:
                return None
            
            return {
                'document_hash': document_hash,
                'owner': owner,
                'timestamp': timestamp,
                'document_type': document_type,
                'exists': exists
            }
        
        except Exception as e:
            return None
    
    def get_user_documents(self, user_id):
        """
        Get all document IDs for a user
        """
        
        user_account = self.get_account_for_user(user_id)
        
        try:
            document_ids = self.contract.functions.getUserDocuments(
                user_account
            ).call()
            
            return list(document_ids)
        
        except Exception as e:
            return []
    
    def get_document_count(self, user_id):
        """
        Get total number of documents for a user
        """
        
        user_account = self.get_account_for_user(user_id)
        
        try:
            count = self.contract.functions.getDocumentCount(
                user_account
            ).call()
            return count
        
        except Exception as e:
            return 0
    
    def _get_private_key(self, account):
        """
        Get private key from environment variables for the specified account.
        
        SECURITY WARNING: This is for development with Ganache only!
        In production, use a proper key management system like:
        - AWS KMS (Key Management Service)
        - HashiCorp Vault
        - Azure Key Vault
        - Google Cloud KMS
        
        Args:
            account: Ethereum account address
            
        Returns:
            Private key string
            
        Raises:
            Exception: If private key is not configured
        """
        # Find index of account
        try:
            account_index = self.w3.eth.accounts.index(account)
        except ValueError:
            raise Exception(f"Account {account} not found in available accounts")
        
        # Get private key from environment
        env_key = f'GANACHE_PRIVATE_KEY_{account_index}'
        private_key = os.getenv(env_key)
        
        if not private_key:
            raise Exception(
                f"Private key not configured. Set {env_key} in .env file. "
                "This should only be used in development with Ganache."
            )
        
        return private_key