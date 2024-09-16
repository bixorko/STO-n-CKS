from flask import Flask, request, jsonify
import threading
from flask_cors import CORS
from bots.trading_bot_for_thirty_minute_chart import TradingBotForThirtyMinuteChart
from bots.trading_bot_for_daily_chart import TradingBotForDailyChart
import time

app = Flask(__name__)
CORS(app)

bots = {}  # Maintain a dictionary of bots based on user_id

global_bot_id = 0

def run_bot(user_id, password, xtb_pair, yahoo_pair, chart_interval):
    global global_bot_id

    if chart_interval == '30m':
        bot = TradingBotForThirtyMinuteChart(global_bot_id, user_id, password, xtb_pair, yahoo_pair, chart_interval, "4d", 30, 0.02)
    elif chart_interval == '1d':
        bot = TradingBotForDailyChart(global_bot_id, user_id, password, xtb_pair, yahoo_pair, chart_interval, "30d", 1440, 0.02)

    bots[global_bot_id] = bot  # Store the bot instance
    global_bot_id += 1
    bot.trade()

@app.route('/get_all_bot_info', methods=['GET'])
def get_all_bot_info():
    print(bots)
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

@app.route('/delete_bot/<int:bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    bot = bots.get(bot_id)
    if bot:
        bot.stop() # Stop the bot
        time.sleep(1)  # Allow a little time for the bot to stop; this might not be needed, but just to be safe
        del bots[bot_id]
        return jsonify({"message": f"Bot {bot_id} deleted successfully!"})
    return jsonify({"error": "Bot not found!"}), 404

if __name__ == '__main__':
    app.run(debug=True)
