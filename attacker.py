import random

class Node:
    def __init__(self, name, is_attacker=False, hash_rate=None, delay=None):
        self.name = name
        self.is_attacker = is_attacker
        # If node created as attacker, allow provided hash_rate/delay; otherwise random defaults
        self.hash_rate = hash_rate if (is_attacker and hash_rate is not None) else random.uniform(0.1, 1.0)
        self.delay = delay if (is_attacker and delay is not None) else random.uniform(0.1, 2.0)
        self.mempool = []  # per-node mempool of accepted transactions

    def accept_transaction(self, transaction, blockchain):
        """
        Validate transaction against blockchain state and add to node mempool if valid.
        Returns True if accepted, False otherwise.
        """
        sender = transaction.get('sender')
        receiver = transaction.get('receiver')
        amount = transaction.get('amount')
        if blockchain.validate_transaction(sender, receiver, amount):
            self.mempool.append(transaction)
            return True
        return False
