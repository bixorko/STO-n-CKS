import numpy as np
import pandas as pd
import yfinance as yf
import ta
import logging
from datetime import datetime, timedelta

class XAUUSDTradingStrategy:
    def __init__(self, 
                 symbol='GC=F',  # Gold Futures contract
                 timeframe='1d', 
                 initial_capital=1000):
        """
        Initialize trading strategy with comprehensive setup
        """
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.capital = initial_capital
        
        # Enhanced risk management
        self.max_risk_per_trade = 0.02  # 2% risk per trade
        self.risk_reward_ratio = 2.5    # Target 2.5:1 risk-reward
        
        # Technical indicators configuration
        self.atr_period = 14
        self.rsi_period = 14
        self.bollinger_period = 20
        
    def fetch_historical_data(self, period='2y'):
        """
        Fetch and preprocess historical price data
        """
        try:
            # Fetch data from Yahoo Finance with longer history
            df = yf.download(self.symbol, period=period, interval=self.timeframe)
            
            # Reset index to make date a column
            df = df.reset_index()
            
            # Add comprehensive technical indicators
            df['ATR'] = ta.volatility.average_true_range(
                df['High'], df['Low'], df['Close'], window=self.atr_period
            )
            
            # Multiple Moving Averages
            df['MA_50'] = df['Close'].rolling(window=50).mean()
            df['MA_200'] = df['Close'].rolling(window=200).mean()
            
            # MACD for trend confirmation
            macd = ta.trend.MACD(df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            
            return df
        except Exception as e:
            self.logger.error(f"Data fetch error: {e}")
            return None
    
    def generate_trade_signals(self, data):
        """
        Advanced trade signal generation with multiple confirmation criteria
        """
        latest = data.iloc[-1]
        signals = {
            'long_condition': False,
            'short_condition': False,
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None
        }
        
        # Comprehensive long condition with multiple filters
        long_conditions = [
            latest['Close'] > latest['MA_50'],
            latest['Close'] > latest['MA_200'],
            latest['MACD'] > latest['MACD_signal']  # MACD bullish crossover
        ]
        
        # Comprehensive short condition with multiple filters
        short_conditions = [
            latest['Close'] < latest['MA_50'],
            latest['Close'] < latest['MA_200'],
            latest['MACD'] < latest['MACD_signal']  # MACD bearish crossover
        ]
        
        # Long signal generation
        if all(long_conditions):
            signals['long_condition'] = True
            signals['entry_price'] = latest['Close']
            signals['stop_loss'] = latest['Low'] - latest['ATR'] * 1.5
            signals['take_profit'] = (
                signals['entry_price'] + 
                (signals['entry_price'] - signals['stop_loss']) * self.risk_reward_ratio
            )
        
        # Short signal generation
        if all(short_conditions):
            signals['short_condition'] = True
            signals['entry_price'] = latest['Close']
            signals['stop_loss'] = latest['High'] + latest['ATR'] * 1.5
            signals['take_profit'] = (
                signals['entry_price'] - 
                (signals['stop_loss'] - signals['entry_price']) * self.risk_reward_ratio
            )
        
        return signals
    
    def backtest(self, data):
        """
        Comprehensive backtesting framework
        """
        initial_capital = 1000
        portfolio_value = [initial_capital]
        trades = []
        current_position = None
        
        # Systematic backtest with more sophisticated trade tracking
        for i in range(50, len(data)):  # Start after moving averages are valid
            current_data = data.iloc[:i]
            signals = self.generate_trade_signals(current_data)
            current_price = data.iloc[i]['Close']
            
            # Close existing position if needed
            if current_position:
                # Check stop loss and take profit for existing position
                if current_position['type'] == 'long':
                    if (current_price <= current_position['stop_loss'] or 
                        current_price >= current_position['take_profit']):
                        profit = current_price - current_position['entry']
                        portfolio_value.append(portfolio_value[-1] + profit)
                        trades.append({
                            'type': 'long',
                            'entry': current_position['entry'],
                            'exit': current_price,
                            'profit': profit
                        })
                        current_position = None
                
                elif current_position['type'] == 'short':
                    if (current_price >= current_position['stop_loss'] or 
                        current_price <= current_position['take_profit']):
                        profit = current_position['entry'] - current_price
                        portfolio_value.append(portfolio_value[-1] + profit)
                        trades.append({
                            'type': 'short',
                            'entry': current_position['entry'],
                            'exit': current_price,
                            'profit': profit
                        })
                        current_position = None
            
            # Enter new position
            if not current_position:
                if signals['long_condition']:
                    current_position = {
                        'type': 'long',
                        'entry': signals['entry_price'],
                        'stop_loss': signals['stop_loss'],
                        'take_profit': signals['take_profit']
                    }
                elif signals['short_condition']:
                    current_position = {
                        'type': 'short',
                        'entry': signals['entry_price'],
                        'stop_loss': signals['stop_loss'],
                        'take_profit': signals['take_profit']
                    }
        
        # Calculate comprehensive performance metrics
        total_return = (portfolio_value[-1] - initial_capital) / initial_capital * 100
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
        """
        Main trading strategy execution method
        """
        try:
            historical_data = self.fetch_historical_data()
            if historical_data is not None:
                # Perform backtesting
                performance = self.backtest(historical_data)
                self.logger.info(f"Strategy Performance: {performance}")
                
                # Generate latest signals
                latest_signals = self.generate_trade_signals(historical_data)
                if latest_signals['long_condition']:
                    self.logger.info(f"POTENTIAL LONG SIGNAL: Entry {latest_signals['entry_price']}")
                elif latest_signals['short_condition']:
                    self.logger.info(f"POTENTIAL SHORT SIGNAL: Entry {latest_signals['entry_price']}")
        
        except Exception as e:
            self.logger.error(f"Trading strategy error: {e}")

# Example usage
if __name__ == "__main__":
    strategy = XAUUSDTradingStrategy()
    strategy.run()
    