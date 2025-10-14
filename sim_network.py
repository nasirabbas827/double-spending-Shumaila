import simpy
import random
from attacker import Node
import time
import uuid
import csv
import logging
import json

class NetworkSimulator:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.nodes = {}
        self.env = simpy.Environment()

    def add_node(self, name):
        # create honest node by default; attacker flag toggled later during attack
        self.nodes[name] = Node(name)

    def broadcast_transaction(self, env, transaction, sender):
        """
        Broadcast public tx to all other nodes with per-node delay.
        Each node validates individually and appends to its mempool if valid.
        Yields timeouts representing network propagation.
        Returns a dict of acceptance results per node.
        """
        acceptance = {}
        for node_name, node in self.nodes.items():
            if node_name == sender:
                # sender already created tx; skip (or optionally add to sender mempool)
                continue
            # simulate propagation delay to this node
            yield env.timeout(node.delay)
            accepted = node.accept_transaction(transaction, self.blockchain)
            acceptance[node_name] = accepted
            logging.debug(f"Node {node_name} {'accepted' if accepted else 'rejected'} tx: {transaction.get('tx_id')}")
        return acceptance

    def double_spend_attack(self, env, attacker_name, hash_rate, delay, target, amount):
        """
        Attacker launches double-spend:
        - creates two transactions at the same timestamp (public -> victim, private -> attacker)
        - broadcasts public tx (nodes validate individually and populate mempools)
        - attacker always mines a private chain concurrently (attempts private mining)
        - honest network mines public chain concurrently
        - after simulated mining period, longer chain becomes canonical
        Returns (result_msg, honest_json, attacker_json).
        """
        attacker = self.nodes[attacker_name]
        # mark attacker and override its params
        attacker.is_attacker = True
        attacker.hash_rate = hash_rate
        attacker.delay = delay

        # create simultaneous txs
        tx_id_public = str(uuid.uuid4())
        tx_id_private = str(uuid.uuid4())
        timestamp = time.time()

        public_tx = {
            'tx_id': tx_id_public,
            'sender': attacker_name,
            'receiver': target,
            'amount': amount,
            'timestamp': timestamp
        }
        private_tx = {
            'tx_id': tx_id_private,
            'sender': attacker_name,
            'receiver': attacker_name,
            'amount': amount,
            'timestamp': timestamp
        }

        # print both txs to terminal
        print(f"Public Transaction initiated (visible to victim {target}): {public_tx}")
        print(f"Private Transaction initiated (secret self-transfer): {private_tx}")

        # validate funds once centrally before proceeding
        if not self.blockchain.validate_transaction(attacker_name, target, amount):
            return "Attack failed: Insufficient funds", None, None

        # remove funds immediately as attacker spends them (to simulate mempool reservation)
        self.blockchain.balances[attacker_name] -= amount

        # broadcast public tx to all nodes (each node will decide acceptance)
        acceptance_proc = env.process(self.broadcast_transaction(env, public_tx, attacker_name))
        yield acceptance_proc
        acceptance = acceptance_proc.value if hasattr(acceptance_proc, 'value') else {}

        # Log which nodes accepted
        accepted_nodes = [n for n, ok in acceptance.items() if ok]
        rejected_nodes = [n for n, ok in acceptance.items() if not ok]
        print(f"Nodes that accepted public tx: {accepted_nodes}")
        print(f"Nodes that rejected public tx: {rejected_nodes}")

        # --- Mining simulation: attacker ALWAYS attempts private mining concurrently ---
        # Compute honest power (sum of honest nodes' hash rates)
        honest_power = sum(node.hash_rate for name, node in self.nodes.items() if name != attacker_name)
        total_power = honest_power + hash_rate

        print(f"Honest power: {honest_power}")
        print(f"Attacker hash: {hash_rate}")
        print(f"Total power: {total_power}")

        # Fork starting points (deep copy lists to avoid mutating real chain until a winner)
        honest_chain = [blk.copy() for blk in self.blockchain.chain]
        attacker_chain = [blk.copy() for blk in self.blockchain.chain]

        # Determine number of blocks each side can realistically mine in 'delay' time window
        # Using proportional estimate: blocks ≈ (power * delay) / difficulty (minimum 1)
        attacker_blocks = max(1, int((hash_rate * delay) / max(1.0, self.blockchain.difficulty)))
        honest_blocks = max(1, int((honest_power * delay) / max(1.0, self.blockchain.difficulty)))

        print(f"Attacker will attempt to mine {attacker_blocks} private blocks.")
        print(f"Honest network will attempt to mine {honest_blocks} public blocks.")

        # Attacker mines private chain: first block contains private_tx
        nonce, block_hash = self.blockchain.proof_of_work(
            len(attacker_chain), attacker_chain[-1]['hash'], [private_tx], env.now
        )
        attacker_chain.append({
            'index': len(attacker_chain),
            'timestamp': env.now,
            'transactions': [private_tx],
            'previous_hash': attacker_chain[-1]['hash'],
            'nonce': nonce,
            'hash': block_hash
        })
        print("  Attacker mined private block #1 (with private tx)")

        # Additional private blocks (may be empty)
        for i in range(1, attacker_blocks):
            nonce, block_hash = self.blockchain.proof_of_work(
                len(attacker_chain), attacker_chain[-1]['hash'], [], env.now
            )
            attacker_chain.append({
                'index': len(attacker_chain),
                'timestamp': env.now,
                'transactions': [],
                'previous_hash': attacker_chain[-1]['hash'],
                'nonce': nonce,
                'hash': block_hash
            })
            print(f"  Attacker mined private block #{i+1}")

        # Honest network mines public chain: first block contains public_tx (if at least one node accepted it)
        # We'll include public_tx if ANY node accepted it (otherwise it won't be in honest chain)
        include_public_tx = len(accepted_nodes) > 0
        first_tx_list = [public_tx] if include_public_tx else []

        if include_public_tx:
            nonce, block_hash = self.blockchain.proof_of_work(
                len(honest_chain), honest_chain[-1]['hash'], first_tx_list, env.now
            )
            honest_chain.append({
                'index': len(honest_chain),
                'timestamp': env.now,
                'transactions': first_tx_list,
                'previous_hash': honest_chain[-1]['hash'],
                'nonce': nonce,
                'hash': block_hash
            })
            print("  Honest network mined public block #1 (with public tx)")
        else:
            # If no node accepted the public tx, honest chain may still mine empty blocks
            print("  No node accepted the public tx; honest network will mine empty blocks.")

        # Additional honest blocks
        for i in range(1, honest_blocks):
            nonce, block_hash = self.blockchain.proof_of_work(
                len(honest_chain), honest_chain[-1]['hash'], [], env.now
            )
            honest_chain.append({
                'index': len(honest_chain),
                'timestamp': env.now,
                'transactions': [],
                'previous_hash': honest_chain[-1]['hash'],
                'nonce': nonce,
                'hash': block_hash
            })
            print(f"  Honest network mined public block #{i+1}")

        # Simulate passage of time for mining effort
        # attacker might take slightly longer; honest slightly faster (tunable)
        yield env.timeout(delay * 0.5)

        # Decide winner: longer chain wins; tie -> honest wins (as usual)
        if len(attacker_chain) > len(honest_chain):
            # Attacker succeeds; replace chain with attacker's private chain
            # Adjust balances: attacker recovers funds and victim loses funds
            # Note: careful with double adjustments; this simplistic model applies intended effect
            self.blockchain.balances[attacker_name] += amount  # attacker keeps funds
            if target in self.blockchain.balances:
                self.blockchain.balances[target] -= amount
            self.blockchain.chain = attacker_chain
            self.blockchain.current_transactions = []

            with open('logs.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    tx_id_public, timestamp, attacker_name, target, amount,
                    str(public_tx), str(private_tx), 'Success'
                ])

            result_msg = f"Attack successful! Attacker chain length {len(attacker_chain)} > honest {len(honest_chain)}."
        else:
            # Honest chain wins or tie -> attacker fails
            # Confirm public tx if included
            if include_public_tx:
                if target in self.blockchain.balances:
                    self.blockchain.balances[target] += amount
            # Attacker already subtracted amount earlier; ensure attacker stays debited
            self.blockchain.chain = honest_chain
            self.blockchain.current_transactions = []

            with open('logs.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    tx_id_public, timestamp, attacker_name, target, amount,
                    str(public_tx), str(private_tx), 'Failed'
                ])

            result_msg = f"Attack failed. Honest chain length {len(honest_chain)} >= attacker {len(attacker_chain)}."

        honest_json = json.dumps(honest_chain, indent=2)
        attacker_json = json.dumps(attacker_chain, indent=2)

        print(f"Honest/Public Chain length: {len(honest_chain)}")
        print(f"Attacker Private Chain length: {len(attacker_chain)}")
        return result_msg, honest_json, attacker_json

    def run_double_spend_attack(self, attacker_name, hash_rate, delay, target, amount):
        """Entry point from Flask."""
        process = self.env.process(
            self.double_spend_attack(self.env, attacker_name, hash_rate, delay, target, amount)
        )
        # run until process completes; we allow env to run until there are no events
        self.env.run()
        # process.value holds return tuple from generator
        return process.value
