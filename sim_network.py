import simpy
import random
from attacker import Node

class NetworkSimulator:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.nodes = {}
        self.env = simpy.Environment()

    def add_node(self, name):
        self.nodes[name] = Node(name)

    def broadcast_transaction(self, env, transaction, sender):
        for node_name, node in self.nodes.items():
            if node_name != sender:
                yield env.timeout(node.delay)
                if self.blockchain.validate_transaction(transaction['sender'], transaction['receiver'], transaction['amount']):
                    self.blockchain.current_transactions.append(transaction)

    def double_spend_attack(self, env, attacker_name, hash_rate, delay, target, amount):
        attacker = self.nodes[attacker_name]
        attacker.is_attacker = True
        attacker.hash_rate = hash_rate
        attacker.delay = delay

        # Create conflicting transactions
        honest_tx = self.blockchain.new_transaction(attacker_name, target, amount)
        double_spend_tx = self.blockchain.new_transaction(attacker_name, attacker_name, amount)

        # Broadcast honest transaction
        yield env.process(self.broadcast_transaction(env, honest_tx, attacker_name))

        # Simulate mining competition
        honest_chain = self.blockchain.chain.copy()
        attacker_chain = self.blockchain.chain.copy()

        honest_power = sum(node.hash_rate for name, node in self.nodes.items() if name != attacker_name)
        total_power = honest_power + attacker.hash_rate

        if random.random() < attacker.hash_rate / total_power:
            nonce, block_hash = self.blockchain.proof_of_work(
                len(attacker_chain), attacker_chain[-1]['hash'], [double_spend_tx], env.now
            )
            attacker_chain.append({
                'index': len(attacker_chain),
                'timestamp': env.now,
                'transactions': [double_spend_tx],
                'previous_hash': attacker_chain[-1]['hash'],
                'nonce': nonce,
                'hash': block_hash
            })
            yield env.timeout(attacker.delay)
            print("Attacker Chain:", attacker_chain)
            print("Honest Chain:", honest_chain)
            self.blockchain.chain = attacker_chain
            self.blockchain.current_transactions = []
            return f"Attack successful! Double-spend transaction confirmed. Chain length: {len(attacker_chain)}"
        else:
            nonce, block_hash = self.blockchain.proof_of_work(
                len(honest_chain), honest_chain[-1]['hash'], [honest_tx], env.now
            )
            honest_chain.append({
                'index': len(honest_chain),
                'timestamp': env.now,
                'transactions': [honest_tx],
                'previous_hash': honest_chain[-1]['hash'],
                'nonce': nonce,
                'hash': block_hash
            })
            yield env.timeout(random.uniform(0.1, 2.0))
            print("Attacker Chain:", attacker_chain)
            print("Honest Chain:", honest_chain)
            self.blockchain.chain = honest_chain
            self.blockchain.current_transactions = []
            return f"Attack failed! Honest transaction confirmed. Chain length: {len(honest_chain)}"

    def run_double_spend_attack(self, attacker_name, hash_rate, delay, target, amount):
        process = self.env.process(self.double_spend_attack(self.env, attacker_name, hash_rate, delay, target, amount))
        self.env.run()
        return process.value