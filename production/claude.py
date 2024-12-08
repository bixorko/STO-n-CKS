import sys
import os
import asyncio
import pandas as pd
import ta
import logging
import discord
import traceback
from datetime import datetime
import socket
import ssl
import json

HOST = 'xapi.xtb.com'
PORT = 5124
END = b'\n\n'

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

context = ssl.create_default_context()

s = context.wrap_socket(sock, server_hostname=HOST)

# Use SelectorEventLoop on Windows
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class XAUUSDTradingStrategy:
    def __init__(self, 
                 client,
                 channel_id,
                 xtb_user_id,
                 xtb_password,
                 symbol='GOLD', 
                 timeframe=30, 
                 initial_capital=500,
                 run_interval=1800,
                 leverage=20):
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.client = client
        self.channel_id = channel_id
        self.xtb_user_id = xtb_user_id
        self.xtb_password = xtb_password
        self.symbol = symbol
        self.timeframe = timeframe
        self.capital = initial_capital
        self.run_interval = run_interval
        self.leverage = leverage
        
        # Strict 2% risk per trade
        self.max_risk_per_trade = 0.02
        self.risk_reward_ratio = 2.5

    def calculate_position_size(self, entry_price):
        """
        Calculate position size based on minimum investment of $125 or 2% of capital, whichever is higher.
        """
        investment_amount = max(125, self.capital * self.max_risk_per_trade)  # Minimum $125 or 2% of capital
        position_size = investment_amount / entry_price  # Position size in units
        return position_size
    
    def send(self, parameters):
        packet = json.dumps(parameters)
        s.send(packet.encode("UTF-8"))

        response = b''
        
        while True:
            response += s.recv(8192)
            if END in response:
                break
            
        return json.loads(response[:response.find(END)])

    def login(self):  
        parameters = {
            "command": "login",
            "arguments": {
                "userId": self.xtb_user_id, 
                "password": self.xtb_password
            }
        }

        return self.send(parameters)
    
    def getChartLastRequest(self):
        parameters = {
            "command": "getChartLastRequest",
            "arguments": {
                "info": {
                    "period": self.timeframe,
                    "start": 1717711200000,
                    "symbol": self.symbol
                }
            }
        }

        return self.send(parameters)
    
    def normalize_price_data(self, rate_info):
        """
        Normalize price data by calculating the actual close, high, and low prices
        based on the open price and the differences provided.
        """
        # The `open` price with two decimal places
        rate_info['open'] = rate_info['open'] / 100
        
        # Calculate actual prices using the differences
        rate_info['close'] = rate_info['open'] + (rate_info['close'] / 100)
        rate_info['high'] = rate_info['open'] + (rate_info['high'] / 100)
        rate_info['low'] = rate_info['open'] + (rate_info['low'] / 100)
        
        return rate_info


    def fetch_historical_data(self):
        try:
            data = self.login()
            data = self.getChartLastRequest()

            if not data.get('status', False):
                raise ValueError("API returned status=False")

            rate_infos = data.get('returnData', {}).get('rateInfos', [])
            
            if not rate_infos:
                raise ValueError("No rateInfos data found in API response")

            # Normalize the rateInfos data to calculate real prices
            normalized_rate_infos = [self.normalize_price_data(info) for info in rate_infos]

            # Convert API data to pandas DataFrame
            df = pd.DataFrame(normalized_rate_infos)

            # Map fields to match expected column names
            df['Date'] = pd.to_datetime(df['ctm'], unit='ms')  # Convert timestamp to datetime
            df.rename(columns={
                'open': 'Open',
                'close': 'Close',
                'high': 'High',
                'low': 'Low',
                'vol': 'Volume'
            }, inplace=True)

            # Sort by date and set index
            df.sort_values('Date', inplace=True)
            df.set_index('Date', inplace=True)

            # Add technical indicators
            df['ATR'] = ta.volatility.average_true_range(
                df['High'], df['Low'], df['Close'], window=14
            )
            df['MA_10'] = df['Close'].rolling(window=10).mean()
            df['MA_50'] = df['Close'].rolling(window=50).mean()

            macd = ta.trend.MACD(df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()

            return df
        except Exception as e:
            self.logger.error(f"Error fetching API data: {e}")
            return None

    def generate_trade_signals(self, data):
        latest = data.iloc[-1]
        signals = {
            'long_condition': False,
            'short_condition': False,
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'position_size': 0
        }
        
        long_conditions = [
            latest['Close'] > latest['MA_10'],
            latest['Close'] > latest['MA_50'],
            latest['MACD'] > latest['MACD_signal']
        ]
        
        short_conditions = [
            latest['Close'] < latest['MA_10'],
            latest['Close'] < latest['MA_50'],
            latest['MACD'] < latest['MACD_signal']
        ]
        
        if all(long_conditions):
            signals['long_condition'] = True
            signals['entry_price'] = latest['Close']
            signals['stop_loss'] = latest['Low'] - latest['ATR'] * 1.5
            signals['take_profit'] = (
                signals['entry_price'] + 
                (signals['entry_price'] - signals['stop_loss']) * self.risk_reward_ratio
            )
            signals['position_size'] = self.calculate_position_size(signals['entry_price'])
        
        if all(short_conditions):
            signals['short_condition'] = True
            signals['entry_price'] = latest['Close']
            signals['stop_loss'] = latest['High'] + latest['ATR'] * 1.5
            signals['take_profit'] = (
                signals['entry_price'] - 
                (signals['stop_loss'] - signals['entry_price']) * self.risk_reward_ratio
            )
            signals['position_size'] = self.calculate_position_size(signals['entry_price'])
        
        return signals
    
    def backtest(self, data):
        initial_capital = self.capital
        portfolio_value = initial_capital
        trades = []
        current_position = None
        total_profit_account = 0  # Track total profit at account level
        
        for i in range(10, len(data)):
            current_data = data.iloc[:i] 
            signals = self.generate_trade_signals(current_data)
            current_row = data.iloc[i]
            
            if current_position:
                if current_position['type'] == 'long':
                    if (current_row['Low'] <= current_position['stop_loss'] or 
                        current_row['High'] >= current_position['take_profit']):
                        
                        if current_row['Low'] <= current_position['stop_loss']:
                            exit_price = current_position['stop_loss']
                            profit = (exit_price - current_position['entry']) * current_position['size']
                            trade_result = 'loss'
                        else:
                            exit_price = current_position['take_profit']
                            profit = (exit_price - current_position['entry']) * current_position['size']
                            trade_result = 'profit'
                        
                        profit_account = profit * self.leverage
                        portfolio_value += profit_account
                        total_profit_account += profit_account
                        
                        trades.append({
                            'type': 'long',
                            'entry': current_position['entry'],
                            'exit': exit_price,
                            'profit': profit_account,
                            'result': trade_result
                        })
                        
                        initial_investment = current_position['entry'] * current_position['size']
                        print(f"{portfolio_value} Trade closed: Type=Long, Entry={current_position['entry']}, Exit={exit_price}, Profit={profit_account}, Result={trade_result}, Initial Investment (Account)={initial_investment}")
                        
                        self.capital = portfolio_value
                        current_position = None
                
                elif current_position['type'] == 'short':
                    if (current_row['High'] >= current_position['stop_loss'] or 
                        current_row['Low'] <= current_position['take_profit']):
                        
                        if current_row['High'] >= current_position['stop_loss']:
                            exit_price = current_position['stop_loss']
                            profit = (current_position['entry'] - exit_price) * current_position['size']
                            trade_result = 'loss'
                        else:
                            exit_price = current_position['take_profit']
                            profit = (current_position['entry'] - exit_price) * current_position['size']
                            trade_result = 'profit'
                        
                        profit_account = profit * self.leverage
                        portfolio_value += profit_account
                        total_profit_account += profit_account
                        
                        trades.append({
                            'type': 'short',
                            'entry': current_position['entry'],
                            'exit': exit_price,
                            'profit': profit_account,
                            'result': trade_result
                        })
                        
                        initial_investment = current_position['entry'] * current_position['size']
                        print(f"{portfolio_value} Trade closed: Type=Short, Entry={current_position['entry']}, Exit={exit_price}, Profit={profit_account}, Result={trade_result}, Initial Investment (Account)={initial_investment}")
                        
                        self.capital = portfolio_value
                        current_position = None
            
            if not current_position:
                if signals['long_condition']:
                    current_position = {
                        'type': 'long',
                        'entry': signals['entry_price'],
                        'stop_loss': signals['stop_loss'],
                        'take_profit': signals['take_profit'],
                        'size': signals['position_size']
                    }
                    print(f"New long position: Entry={signals['entry_price']}, Stop Loss={signals['stop_loss']}, Take Profit={signals['take_profit']}, Position Size={signals['position_size']}")
                elif signals['short_condition']:
                    current_position = {
                        'type': 'short',
                        'entry': signals['entry_price'],
                        'stop_loss': signals['stop_loss'],
                        'take_profit': signals['take_profit'],
                        'size': signals['position_size']
                    }
                    print(f"New short position: Entry={signals['entry_price']}, Stop Loss={signals['stop_loss']}, Take Profit={signals['take_profit']}, Position Size={signals['position_size']}")
        
        total_return = (portfolio_value - initial_capital) / initial_capital * 100
        profitable_trades = [trade for trade in trades if trade['result'] == 'profit']
        losing_trades = [trade for trade in trades if trade['result'] == 'loss']
        
        return {
            'total_return_percentage': round(total_return, 2),
            'total_trades': len(trades),
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(profitable_trades) / len(trades) * 100, 2) if trades else 0,
            'total_profit': round(total_profit_account, 2),
            'average_profit_per_trade': round(total_profit_account / len(trades), 2) if trades else 0,
            'final_portfolio_value': round(portfolio_value, 2)
        }

    async def send_discord_alert(self, signals=None, performance=None):
        try:
            channel = self.client.get_channel(self.channel_id)
            if not channel:
                self.logger.error("Could not find the specified Discord channel")
                return

            if performance:
                performance_message = f"""
```
📊 Backtest Performance Report 📈
======================
Total Return: {performance['total_return_percentage']}%
Total Trades: {performance['total_trades']}
Profitable Trades: {performance['profitable_trades']}
Win Rate: {performance['win_rate']}%
Total Profit: ${performance['total_profit']}
Avg Profit/Trade: ${performance['average_profit_per_trade']}
======================
```
"""
                await channel.send(performance_message)

            if signals and (signals['long_condition'] or signals['short_condition']):
                trade_type = 'LONG 🟢' if signals['long_condition'] else 'SHORT 🔴'
                signal_message = f"""
```
Stock Signal Alert 🚀
======================
Stock: {self.symbol} 🌟
Date: {datetime.now().strftime('%Y-%m-%d')}
Trade Type: {trade_type}
Opening Price: ${signals['entry_price']:.2f} 💸
Take Profit (TP): ${signals['take_profit']:.2f} 🍋
Stop Loss (SL): ${signals['stop_loss']:.2f} ⚠️
Position Size: {signals['position_size']:.2f}
======================
```
"""
                await channel.send(signal_message)

        except Exception as e:
            self.logger.error(f"Error sending Discord alert: {e}")

    async def run_continuous(self):
        await self.client.wait_until_ready()

        while not self.client.is_closed():
            try:
                historical_data = self.fetch_historical_data()
                if historical_data is not None:
                    performance = self.backtest(historical_data)
                    await self.send_discord_alert(performance=performance)
                    self.logger.info(f"Strategy Performance: {performance}")

                    latest_signals = self.generate_trade_signals(historical_data)
                    if latest_signals['long_condition'] or latest_signals['short_condition']:
                        await self.send_discord_alert(signals=latest_signals)

                await asyncio.sleep(self.run_interval)
            except Exception as e:
                error_message = f"""
```
❌ Trading Strategy Error ❌
======================
Error: {str(e)}
Traceback: {traceback.format_exc()}
======================
```
"""
                channel = self.client.get_channel(self.channel_id)
                await channel.send(error_message)
                self.logger.error(f"Trading strategy error: {e}")
                await asyncio.sleep(self.run_interval)


def main():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
    XTB_USER_ID = os.getenv('XTB_USER_ID')
    XTB_PASSWORD = os.getenv('XTB_PASSWORD')

    strategy = None

    @client.event
    async def on_ready():
        nonlocal strategy
        print(f'Logged in as {client.user}')
        strategy = XAUUSDTradingStrategy(
            client=client,
            channel_id=CHANNEL_ID,
            xtb_user_id=XTB_USER_ID,
            xtb_password=XTB_PASSWORD,
            symbol='GOLD',
            run_interval=1800
        )
        client.loop.create_task(strategy.run_continuous())

    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
