from flask import Flask, render_template, request, jsonify, send_file , url_for
from blockchain import Blockchain
from sim_network import NetworkSimulator
import uuid
import logging
import csv
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
from io import BytesIO
import base64



app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

blockchain = Blockchain(difficulty=4)
simulator = NetworkSimulator(blockchain)

nodes = ['Anas', 'Hamid', 'Haider', 'Nasir', 'Ali', 'Omar']
for node in nodes:
    simulator.add_node(node)

attack_history = []
csv_file = 'logs.csv'
with open(csv_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'transaction id',
        'timestamp',
        'sender',
        'receiver',
        'amount',
        'public transaction details',
        'private transaction details',
        'Attack Result'
    ])

last_honest_chain = None
last_attacker_chain = None
last_attack_result = None

@app.route('/')
def index():
    node_data = [{'name': name, 'hash_rate': simulator.nodes[name].hash_rate} for name in nodes]
    return render_template('index.html', nodes=node_data)

@app.route('/transactions')
def transactions():
    chain = blockchain.chain
    logging.debug(f"Chain length: {len(chain)}, Chain: {chain}")
    return render_template('transactions.html', chain=chain, 
                           honest_chain=last_honest_chain, attacker_chain=last_attacker_chain, 
                           attack_result=last_attack_result)

@app.route('/attack', methods=['GET', 'POST'])
def attack():
    global last_honest_chain, last_attacker_chain, last_attack_result
    if request.method == 'POST':
        attacker = request.form['attacker']
        hash_rate = float(request.form['hash_rate'])
        delay = float(request.form['delay'])
        target = request.form['target']
        amount = float(request.form['amount'])
        
        result_tuple = simulator.run_double_spend_attack(attacker, hash_rate, delay, target, amount)
        result_msg = result_tuple[0]
        honest_chain_json = result_tuple[1]
        attacker_chain_json = result_tuple[2]
        
        last_honest_chain = honest_chain_json
        last_attacker_chain = attacker_chain_json
        last_attack_result = 'Success' if 'successful' in result_msg.lower() else 'Failed'
        
        attack_result = last_attack_result
        attack_history.append({
            'attacker': attacker,
            'hash_rate': hash_rate,
            'delay': delay,
            'target': target,
            'amount': amount,
            'result': attack_result
        })
        logging.debug(f"Attack result: {result_msg}, New chain: {blockchain.chain}")
        return render_template('attack.html', nodes=nodes, result=result_msg, 
                               honest_chain=honest_chain_json, attacker_chain=attacker_chain_json, 
                               attack_history=attack_history)
    return render_template('attack.html', nodes=nodes, attack_history=attack_history)

@app.route('/api/chain', methods=['GET'])
def get_chain():
    return jsonify(blockchain.chain)

@app.route('/download_logs')
def download_logs():
    csv_path = 'logs.csv'
    if os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True, download_name='logs.csv', mimetype='text/csv')
    else:
        return "No logs file found.", 404

@app.route('/visualize')
def visualize():
    csv_path = 'logs.csv'
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if len(df) > 0:
            # ensure numeric conversions if present elsewhere
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
            # Attack Result pie chart (if column exists)
            if 'Attack Result' in df.columns:
                result_counts = df['Attack Result'].value_counts()
                ax1.pie(result_counts, labels=result_counts.index, autopct='%1.1f%%')
                ax1.set_title('Attack Success Rate')
            else:
                ax1.text(0.5, 0.5, 'No Attack Result column', ha='center')
            # If hash_rate/delay columns exist, show averages; otherwise show amounts by result
            if 'hash_rate' in df.columns and 'delay' in df.columns:
                avg_stats = df.groupby('Attack Result')[['hash_rate', 'delay']].mean()
                avg_stats.plot(kind='bar', ax=ax2)
                ax2.set_title('Avg Hash Rate & Delay by Result')
                ax2.set_ylabel('Average')
            elif 'amount' in df.columns:
                avg_amount = df.groupby('Attack Result')['amount'].mean()
                avg_amount.plot(kind='bar', ax=ax2)
                ax2.set_title('Avg Amount by Result')
                ax2.set_ylabel('Average Amount')
            plt.tight_layout()
            plot_path = 'static/plot.png'
            plt.savefig(plot_path)
            plt.close()
            return render_template('visualize.html', has_data=True, plot_url=url_for('static', filename='plot.png'), total_attacks=len(df))
        else:
            return render_template('visualize.html', has_data=False, message="No data.")
    else:
        return render_template('visualize.html', has_data=False, message="No logs.")

if __name__ == '__main__':
    app.run(debug=True)
