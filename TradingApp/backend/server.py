from flask import Flask, request, jsonify
import threading
from flask_cors import CORS
from trade_bot import TradingBot

app = Flask(__name__)
CORS(app)

bots = {}  # Maintain a dictionary of bots based on user_id

global_bot_id = 0

def run_bot(user_id, password, xtb_pair, yahoo_pair, chart_interval):
    global global_bot_id
    bot = TradingBot(user_id, password, xtb_pair, yahoo_pair, chart_interval, "4d", 30, 0.02)
    bots[global_bot_id] = bot  # Store the bot instance
    global_bot_id += 1
    bot.trade()

@app.route('/get_all_bot_info', methods=['GET'])
def get_all_bot_info():
    return jsonify([bot.get_bot_info() for bot in bots.values()])

@app.route('/start_bot', methods=['POST'])
def start_bot():
    data = request.get_json()
    
    user_id = data.get('user_id')
    password = data.get('password')
    xtb_pair = data.get('xtb_pair')
    yahoo_pair = data.get('yahoo_pair')
    chart_interval = data.get('chart_interval')

    threading.Thread(target=run_bot, args=(user_id, password, xtb_pair, yahoo_pair, chart_interval)).start()
    return jsonify({"message": "Bot started!"})

if __name__ == '__main__':
    app.run(debug=True)
