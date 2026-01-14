from web3 import Web3
from django.conf import settings
import json
import os


class BlockchainService:
    """
    Service class to interact with Ganache blockchain
    
    BLOCKCHAIN INTERACTION FLOW:
    1. Connect to Ganache (local blockchain)
    2. Load smart contract (our DocumentRegistry)
    3. Send transactions to contract (register, verify)
    4. Read data from contract (get documents)
    """
    
    def __init__(self):
        # Connect to Ganache
        self.w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_CONFIG['GANACHE_URL']))
        
        # Check connection
        if not self.w3.is_connected():
            raise Exception("Failed to connect to Ganache. Make sure it's running!")
        
        # Enable default account handling (Ganache auto-signs)
        self.w3.eth.default_account = self.w3.eth.accounts[0]
        
        # Load contract
        self.contract = self._load_contract()
        
        # Get default account (we'll use the first Ganache account)
        self.default_account = self.w3.eth.accounts[0]
    
    def _load_contract(self):
        """
        Load the deployed smart contract
        
        WHAT HAPPENS HERE:
        1. Read the contract ABI (interface definition)
        2. Get the contract address (where it's deployed)
        3. Create contract instance we can interact with
        """
        
        # Path to compiled contract (after truffle migrate)
        contract_path = os.path.join(
            settings.BASE_DIR,
            'blockchain_project',
            'build',
            'contracts',
            'DocumentRegistry.json'
        )
        
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
        Get private key for Ganache account
        
        GANACHE GIVES US THESE FOR TESTING
        In production, NEVER hardcode private keys!
        """
        # Ganache deterministic private keys (these are publicly known test keys)
        ganache_keys = [
            '0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d',
            '0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1',
            '0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c',
            '0x646f1ce2fdad0e6deeeb5c7e8e5543bdde65e86029e2fd9fc169899c440a7913',
            '0xadd53f9a7e588d003326d1cbf9e4a43c061aadd9bc938c843a79e7b4fd2ad743',
            '0x395df67f0c2d2d9fe1ad08d1bc8b6627011959b79c53d7dd6a3536a33ab8a4fd',
            '0xe485d098507f54e7733a205420dfddbe58db035fa577fc294ebd14db90767a52',
            '0xa453611d9419d0e56f499079478fd72c37b251a94bfde4d19872c44cf65386e3',
            '0x829e924fdf021ba3dbbc4225edfece9aca04b929d6e75613329ca6f1d31c0bb4',
            '0xb0057716d5917badaf911b193b12b910811c1497b5bada8d7711f758981c3773'
        ]
        
        # Find index of account
        account_index = self.w3.eth.accounts.index(account)
        return ganache_keys[account_index]