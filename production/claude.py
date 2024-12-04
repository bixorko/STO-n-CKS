import numpy as np
import pandas as pd
import yfinance as yf
import ta
import logging

class XAUUSDTradingStrategy:
    def __init__(self, 
                 symbol='GC=F', 
                 timeframe='1d', 
                 initial_capital=1000):
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.capital = initial_capital
        
        # Strict 2% risk per trade
        self.max_risk_per_trade = 1
        self.risk_reward_ratio = 2.5

    def calculate_position_size(self, entry_price, stop_loss):
        """
        Calculate position size based on 2% risk per trade
        """
        risk_amount = self.capital * self.max_risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        
        # Calculate number of shares/contracts
        position_size = risk_amount / price_risk
        
        return position_size

    def fetch_historical_data(self, period='2y'):
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
            signals['position_size'] = self.calculate_position_size(
                signals['entry_price'], signals['stop_loss']
            )
        
        if all(short_conditions):
            signals['short_condition'] = True
            signals['entry_price'] = latest['Close']
            signals['stop_loss'] = latest['High'] + latest['ATR'] * 1.5
            signals['take_profit'] = (
                signals['entry_price'] - 
                (signals['stop_loss'] - signals['entry_price']) * self.risk_reward_ratio
            )
            signals['position_size'] = self.calculate_position_size(
                signals['entry_price'], signals['stop_loss']
            )
        
        return signals
    
    def backtest(self, data):
        initial_capital = self.capital
        portfolio_value = initial_capital
        trades = []
        current_position = None
        
        for i in range(50, len(data)):
            current_data = data.iloc[:i]
            signals = self.generate_trade_signals(current_data)
            current_price = data.iloc[i]['Close']
            
            if current_position:
                if current_position['type'] == 'long':
                    if current_price <= current_position['stop_loss'] or current_price >= current_position['take_profit']:
                        profit = (current_price - current_position['entry']) * current_position['size']
                        portfolio_value += profit
                        trades.append({
                            'type': 'long',
                            'entry': current_position['entry'],
                            'exit': current_price,
                            'profit': profit
                        })
                        current_position = None
                
                elif current_position['type'] == 'short':
                    if current_price >= current_position['stop_loss'] or current_price <= current_position['take_profit']:
                        profit = (current_position['entry'] - current_price) * current_position['size']
                        portfolio_value += profit
                        trades.append({
                            'type': 'short',
                            'entry': current_position['entry'],
                            'exit': current_price,
                            'profit': profit
                        })
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
                elif signals['short_condition']:
                    current_position = {
                        'type': 'short',
                        'entry': signals['entry_price'],
                        'stop_loss': signals['stop_loss'],
                        'take_profit': signals['take_profit'],
                        'size': signals['position_size']
                    }
        
        total_return = (portfolio_value - initial_capital) / initial_capital * 100
        profitable_trades = [trade for trade in trades if trade['profit'] > 0]
        
        return {
            'total_return_percentage': round(total_return, 2),
            'total_trades': len(trades),
            'profitable_trades': len(profitable_trades),
            'win_rate': round(len(profitable_trades) / len(trades) * 100, 2) if trades else 0,
            'total_profit': round(sum(trade['profit'] for trade in trades), 2),
            'average_profit_per_trade': round(sum(trade['profit'] for trade in trades) / len(trades), 2) if trades else 0
        }
    
    def run(self):
        try:
            historical_data = self.fetch_historical_data()
            if historical_data is not None:
                performance = self.backtest(historical_data)
                self.logger.info(f"Strategy Performance: {performance}")
                
                latest_signals = self.generate_trade_signals(historical_data)
                if latest_signals['long_condition']:
                    self.logger.info(f"POTENTIAL LONG SIGNAL: Entry {latest_signals['entry_price']}, Position Size {latest_signals['position_size']}")
                elif latest_signals['short_condition']:
                    self.logger.info(f"POTENTIAL SHORT SIGNAL: Entry {latest_signals['entry_price']}, Position Size {latest_signals['position_size']}")
        
        except Exception as e:
            self.logger.error(f"Trading strategy error: {e}")

if __name__ == "__main__":
    strategy = XAUUSDTradingStrategy()
    strategy.run()
