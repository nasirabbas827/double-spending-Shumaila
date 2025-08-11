from flask import Flask, render_template, request, jsonify
from blockchain import Blockchain
from sim_network import NetworkSimulator
import uuid
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Initialize blockchain and simulator
blockchain = Blockchain(difficulty=4)
simulator = NetworkSimulator(blockchain)

# Add nodes: Anas, Hamid, Haider
nodes = ['Anas', 'Hamid', 'Haider', 'Nasir']
for node in nodes:
    simulator.add_node(node)

# Add 7 initial transactions after genesis block
initial_transactions = [
    {"sender": "Anas", "receiver": "Hamid", "amount": 10},
    {"sender": "Hamid", "receiver": "Haider", "amount": 5},
    {"sender": "Haider", "receiver": "Anas", "amount": 15},
    {"sender": "Anas", "receiver": "Haider", "amount": 20},
    {"sender": "Hamid", "receiver": "Anas", "amount": 8},
    {"sender": "Haider", "receiver": "Hamid", "amount": 12},
    {"sender": "Anas", "receiver": "Hamid", "amount": 7}
]
for tx in initial_transactions:
    if blockchain.validate_transaction(tx["sender"], tx["receiver"], tx["amount"]):
        blockchain.new_transaction(tx["sender"], tx["receiver"], tx["amount"])
        blockchain.mine_block()
        logging.debug(f"Added transaction: {tx}, Block: {blockchain.chain[-1]}")
    else:
        logging.error(f"Invalid transaction: {tx}")

# Store attack history
attack_history = []

@app.route('/')
def index():
    # Create a list of dictionaries with node names and their hash rates
    node_data = [{'name': name, 'hash_rate': simulator.nodes[name].hash_rate} for name in nodes]
    return render_template('index.html', nodes=node_data)

@app.route('/transactions')
def transactions():
    chain = blockchain.chain
    logging.debug(f"Chain length: {len(chain)}, Chain: {chain}")
    return render_template('transactions.html', chain=chain)

@app.route('/attack', methods=['GET', 'POST'])
def attack():
    if request.method == 'POST':
        attacker = request.form['attacker']
        hash_rate = float(request.form['hash_rate'])
        delay = float(request.form['delay'])
        target = request.form['target']
        amount = float(request.form['amount'])
        
        result = simulator.run_double_spend_attack(attacker, hash_rate, delay, target, amount)
        # Add to attack history
        attack_history.append({
            'attacker': attacker,
            'hash_rate': hash_rate,
            'delay': delay,
            'target': target,
            'amount': amount,
            'result': 'Success' if 'successful' in result.lower() else 'Failed'
        })
        logging.debug(f"Attack result: {result}, New chain: {blockchain.chain}")
        return render_template('attack.html', nodes=nodes, result=result, attack_history=attack_history)
    return render_template('attack.html', nodes=nodes, attack_history=attack_history)

@app.route('/api/chain', methods=['GET'])
def get_chain():
    return jsonify(blockchain.chain)

if __name__ == '__main__':
    app.run(debug=True)