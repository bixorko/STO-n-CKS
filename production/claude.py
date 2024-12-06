import sys
import os
import asyncio
import yfinance as yf
import ta
import logging
import discord
import traceback
from datetime import datetime

# Use SelectorEventLoop on Windows
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class XAUUSDTradingStrategy:
    def __init__(self, 
                 client,
                 channel_id,
                 symbol='GC=F', 
                 timeframe='30m', 
                 initial_capital=500,
                 run_interval=1800,  # Default 0.5 hour interval
                 leverage=20):
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.client = client
        self.channel_id = channel_id
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

    def fetch_historical_data(self, period='1mo'):
        try:
            df = yf.download(self.symbol, period=period, interval=self.timeframe)
            df = df.reset_index()
            
            df['ATR'] = ta.volatility.average_true_range(
                df['High'], df['Low'], df['Close'], window=14
            )
            
            df['MA_50'] = df['Close'].rolling(window=50).mean()
            df['MA_200'] = df['Close'].rolling(window=200).mean()
            
            macd = ta.trend.MACD(df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            
            return df
        except Exception as e:
            self.logger.error(f"Data fetch error: {e}")
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
            latest['Close'] > latest['MA_50'],
            latest['Close'] > latest['MA_200'],
            latest['MACD'] > latest['MACD_signal']
        ]
        
        short_conditions = [
            latest['Close'] < latest['MA_50'],
            latest['Close'] < latest['MA_200'],
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
        
        for i in range(50, len(data)):
            current_data = data.iloc[:i] 
            signals = self.generate_trade_signals(current_data)
            current_row = data.iloc[i]
            
            if current_position:
                if current_position['type'] == 'long':
                    # Check if stop loss or take profit was hit during the candle
                    if (current_row['Low'] <= current_position['stop_loss'] or 
                        current_row['High'] >= current_position['take_profit']):
                        
                        # Determine exit price based on stop loss or take profit
                        if current_row['Low'] <= current_position['stop_loss']:
                            exit_price = current_position['stop_loss']
                            profit = (exit_price - current_position['entry']) * current_position['size']
                            trade_result = 'loss'
                        else:
                            exit_price = current_position['take_profit']
                            profit = (exit_price - current_position['entry']) * current_position['size']
                            trade_result = 'profit'
                        
                        # Apply leverage to profit and update portfolio value
                        profit_account = profit * self.leverage  # Profit at account level with leverage applied
                        portfolio_value += profit_account
                        total_profit_account += profit_account
                        
                        trades.append({
                            'type': 'long',
                            'entry': current_position['entry'],
                            'exit': exit_price,
                            'profit': profit_account,
                            'result': trade_result
                        })
                        
                        # Print trade details
                        initial_investment = current_position['entry'] * current_position['size']
                        print(f"Trade closed: Type=Long, Entry={current_position['entry']}, Exit={exit_price}, Profit={profit_account}, Result={trade_result}, Initial Investment (Account)={initial_investment}")
                        
                        # Update capital for next trades based on trade outcome
                        self.capital = portfolio_value
                        current_position = None
                
                elif current_position['type'] == 'short':
                    # Check if stop loss or take profit was hit during the candle
                    if (current_row['High'] >= current_position['stop_loss'] or 
                        current_row['Low'] <= current_position['take_profit']):
                        
                        # Determine exit price based on stop loss or take profit
                        if current_row['High'] >= current_position['stop_loss']:
                            exit_price = current_position['stop_loss']
                            profit = (current_position['entry'] - exit_price) * current_position['size']
                            trade_result = 'loss'
                        else:
                            exit_price = current_position['take_profit']
                            profit = (current_position['entry'] - exit_price) * current_position['size']
                            trade_result = 'profit'
                        
                        # Apply leverage to profit and update portfolio value
                        profit_account = profit * self.leverage  # Profit at account level with leverage applied
                        portfolio_value += profit_account
                        total_profit_account += profit_account
                        
                        trades.append({
                            'type': 'short',
                            'entry': current_position['entry'],
                            'exit': exit_price,
                            'profit': profit_account,
                            'result': trade_result
                        })
                        
                        # Print trade details
                        initial_investment = current_position['entry'] * current_position['size']
                        print(f"Trade closed: Type=Short, Entry={current_position['entry']}, Exit={exit_price}, Profit={profit_account}, Result={trade_result}, Initial Investment (Account)={initial_investment}")
                        
                        # Update capital for next trades based on trade outcome
                        self.capital = portfolio_value
                        current_position = None
            
            # Enter new position if no current position
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

    async def send_discord_alert(self, signals=None, performance=None, latest_data=None):
        """
        Send trading signal or backtest alert to Discord
        """
        try:
            channel = self.client.get_channel(self.channel_id)
            if not channel:
                self.logger.error("Could not find the specified Discord channel")
                return

            # Backtest Performance Message
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

            # Trading Signal Message
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
        """
        Continuously run the trading strategy
        """
        await self.client.wait_until_ready()
        
        while not self.client.is_closed():
            try:
                # Fetch historical data
                historical_data = self.fetch_historical_data()
                
                if historical_data is not None:
                    # Run backtest
                    performance = self.backtest(historical_data)
                    
                    # Send backtest performance to Discord
                    await self.send_discord_alert(performance=performance)
                    self.logger.info(f"Strategy Performance: {performance}")
                    
                    # Generate latest signals
                    latest_signals = self.generate_trade_signals(historical_data)
                    
                    # Send signal alerts to Discord
                    if latest_signals['long_condition'] or latest_signals['short_condition']:
                        await self.send_discord_alert(signals=latest_signals, latest_data=historical_data.iloc[-1])
                
                # Wait before next iteration
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
                
                # Wait before retrying
                await asyncio.sleep(self.run_interval)

def main():
    # Discord bot setup
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    # Get environment variables
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

    # Create trading strategy instance
    strategy = None

    @client.event
    async def on_ready():
        nonlocal strategy
        print(f'Logged in as {client.user}')
        
        # Initialize strategy after bot is ready
        strategy = XAUUSDTradingStrategy(
            client=client,
            channel_id=CHANNEL_ID,
            symbol='GC=F',  # Gold Futures
            run_interval=3600  # Run every hour
        )
        
        # Start the continuous running of the strategy
        client.loop.create_task(strategy.run_continuous())

    # Run the bot
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()