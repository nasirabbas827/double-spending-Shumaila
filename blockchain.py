import hashlib
import time
import json

class Blockchain:
    def __init__(self, difficulty=4):
        self.chain = []
        self.current_transactions = []
        self.difficulty = difficulty
        self.balances = {'Anas': 100, 'Hamid': 100, 'Haider': 100, 'Nasir': 100, 'Ali': 100, 'Omar': 100}
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = {
            'index': 0,
            'timestamp': time.time(),
            'transactions': [],
            'previous_hash': '0',
            'nonce': 0,
            'hash': self.compute_hash(0, '0', [], time.time(), 0)
        }
        self.chain.append(genesis_block)

    def compute_hash(self, index, previous_hash, transactions, timestamp, nonce):
        block_string = f"{index}{previous_hash}{json.dumps(transactions)}{timestamp}{nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def proof_of_work(self, index, previous_hash, transactions, timestamp):
        nonce = 0
        while True:
            hash_result = self.compute_hash(index, previous_hash, transactions, timestamp, nonce)
            if hash_result.startswith('0' * self.difficulty):
                return nonce, hash_result
            nonce += 1

    def validate_transaction(self, sender, receiver, amount):
        if sender == receiver or amount <= 0:
            return False
        if sender not in self.balances or self.balances[sender] < amount:
            return False
        return True

    def new_transaction(self, sender, receiver, amount):
        transaction = {
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
            'timestamp': time.time()
        }
        self.current_transactions.append(transaction)
        return transaction

    def mine_block(self):
        last_block = self.chain[-1]
        index = last_block['index'] + 1
        timestamp = time.time()
        transactions = self.current_transactions
        previous_hash = last_block['hash']
        nonce, block_hash = self.proof_of_work(index, previous_hash, transactions, timestamp)
        
        block = {
            'index': index,
            'timestamp': timestamp,
            'transactions': transactions,
            'previous_hash': previous_hash,
            'nonce': nonce,
            'hash': block_hash
        }
        self.chain.append(block)
        self.current_transactions = []
        return block