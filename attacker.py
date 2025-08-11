import random

class Node:
    def __init__(self, name, is_attacker=False, hash_rate=None, delay=None):
        self.name = name
        self.is_attacker = is_attacker
        self.hash_rate = hash_rate if is_attacker else random.uniform(0.1, 1.0)
        self.delay = delay if is_attacker else random.uniform(0.1, 2.0)