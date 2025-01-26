import os
import pandas as pd
import ta
import logging
import socket
import ssl
import time
import json
import threading

HOST = 'xapi.xtb.com'
PORT = 5112
END = b'\n\n'

class XAUUSDTradingStrategy:
    def __init__(self, 
                 xtb_user_id,
                 xtb_password,
                 pip_value,
                 trade_volume,
                 symbol='GOLD', 
                 use_dynamic_rr=True,
                 timeframe=30, 
                 chart_start_from=1717711200000,
                 initial_capital=500,
                 run_interval=1800,
                 leverage=20):
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        self.context = ssl.create_default_context()

        self.s = self.context.wrap_socket(self.sock, server_hostname=HOST)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.xtb_user_id = xtb_user_id
        self.xtb_password = xtb_password
        self.symbol = symbol
        self.pip_value = pip_value
        self.decimal_places = len(str(self.pip_value).split(".")[1]) if "." in str(self.pip_value) else 0
        self.trade_volume = trade_volume
        self.use_dynamic_rr = use_dynamic_rr
        self.timeframe = timeframe
        self.chart_start_from = chart_start_from
        self.capital = initial_capital
        self.run_interval = run_interval
        self.leverage = leverage
        
        # Strict 2% risk per trade
        self.max_risk_per_trade = 0.02
        self.risk_reward_ratio = 1

    def calculate_position_size(self, entry_price):
        """
        Calculate position size based on minimum investment of $125 or 2% of capital, whichever is higher.
        """
        investment_amount = max(125, self.capital * self.max_risk_per_trade)  # Minimum $125 or 2% of capital
        position_size = investment_amount / entry_price  # Position size in units
        return position_size
    
    def send(self, parameters):
        packet = json.dumps(parameters)
        self.s.send(packet.encode("UTF-8"))

        response = b''
        
        while True:
            response += self.s.recv(8192)
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

    def getTrades(self):
        self.login()

        parameters = {
            "command": "getTrades",
            "arguments": {
                "openedOnly": True
            }
        }

        return self.send(parameters)
    
    def getChartLastRequest(self):
        self.login()

        parameters = {
            "command": "getChartLastRequest",
            "arguments": {
                "info": {
                    "period": self.timeframe,
                    "start": self.chart_start_from,
                    "symbol": self.symbol
                }
            }
        }

        return self.send(parameters)
    
    def execute_trade_transaction(self, cmd, stop_loss, take_profit, volume):
        self.login()

        parameters = {
            "command": "tradeTransaction",
            "arguments": {
                "tradeTransInfo": {
                    "cmd": cmd,  # 0 for buy, 1 for sell
                    "symbol": self.symbol,
                    "price": 1, # needs to be in arguments, however with direct buy / sell command (0/1) is this attribute ignored and the current bid / ask price is used
                    "sl": round(stop_loss, self.decimal_places),
                    "tp": round(take_profit, self.decimal_places),
                    "volume": volume
                }
            }
        }

        response = self.send(parameters)
        if response.get('status', False):
            self.logger.info(f"Trade executed successfully: {response}")
        else:
            self.logger.error(f"Trade execution failed: {response}")

        return response

    
    def normalize_price_data(self, rate_info):
        """
        Normalize price data by calculating the actual close, high, and low prices
        based on the open price and the differences provided.
        """
        # The `open` price with two decimal places
        rate_info['open'] = rate_info['open'] * self.pip_value
        
        # Calculate actual prices using the differences
        rate_info['close'] = rate_info['open'] + (rate_info['close'] * self.pip_value)
        rate_info['high'] = rate_info['open'] + (rate_info['high'] * self.pip_value)
        rate_info['low'] = rate_info['open'] + (rate_info['low'] * self.pip_value)
        
        return rate_info


    def fetch_historical_data(self):
        try:
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

            macd = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            df['MACD_hist'] = macd.macd_diff()

            # Momentum indicators
            df['Stoch_K'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'], window=14, smooth_window=3)
            df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()

            # Volume indicators
            df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])

            # Volatility ratio for market regime detection
            df['Volatility_Ratio'] = df['ATR'] / df['Close'] * 100

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
            'position_size': 0,
            'signal_strength': 0  # New field for signal strength
        }
        
        # Market regime detection
        is_volatile = latest['Volatility_Ratio'] > 1.5
        
        # Base conditions
        long_conditions = [
            latest['Close'] > latest['MA_10'],
            latest['Close'] > latest['MA_50'],
            latest['MACD'] > latest['MACD_signal'],
            latest['Stoch_K'] > latest['Stoch_D'],
            latest['OBV'] > data['OBV'].rolling(window=20).mean().iloc[-1]  # Volume confirmation
        ]
        
        short_conditions = [
            latest['Close'] < latest['MA_10'],
            latest['Close'] < latest['MA_50'],
            latest['MACD'] < latest['MACD_signal'],
            latest['Stoch_K'] < latest['Stoch_D'],
            latest['OBV'] < data['OBV'].rolling(window=20).mean().iloc[-1]  # Volume confirmation
        ]
        
        # Dynamic ATR multiplier based on volatility
        atr_multiplier = 1.5
        if is_volatile:
            atr_multiplier = 2.0
        
        # Calculate signal strength (0-100)
        def calculate_signal_strength(conditions, latest_data):
            base_strength = sum(conditions) / len(conditions) * 100
            
            # Additional strength factors
            momentum_factor = min(abs(latest_data['MACD_hist']) / 0.001 * 10, 20)
            volume_factor = min((latest_data['Volume'] / data['Volume'].rolling(window=20).mean().iloc[-1] - 1) * 20, 20)
            trend_strength = min(abs(latest_data['Close'] - latest_data['MA_50']) / latest_data['ATR'] * 5, 20)
            
            return base_strength + momentum_factor + volume_factor + trend_strength
        
        if all(long_conditions):
            signals['long_condition'] = True
            signals['entry_price'] = latest['Close']
            signals['stop_loss'] = latest['Low'] - latest['ATR'] * atr_multiplier
            
            # Dynamic risk-reward ratio based on signal strength
            signal_strength = calculate_signal_strength(long_conditions, latest)
            signals['signal_strength'] = signal_strength
            if self.use_dynamic_rr:
                dynamic_rr_ratio = self.risk_reward_ratio * (1 + (signal_strength / 100))
            else:
                dynamic_rr_ratio = 1
            
            signals['take_profit'] = (
                signals['entry_price'] + 
                (signals['entry_price'] - signals['stop_loss']) * dynamic_rr_ratio
            )
            
            # Position sizing based on signal strength and volatility
            signals['position_size'] = self.calculate_position_size(signals['entry_price'])
        
        if all(short_conditions):
            signals['short_condition'] = True
            signals['entry_price'] = latest['Close']
            signals['stop_loss'] = latest['High'] + latest['ATR'] * atr_multiplier
            
            signal_strength = calculate_signal_strength(short_conditions, latest)
            signals['signal_strength'] = signal_strength
            if self.use_dynamic_rr:
                dynamic_rr_ratio = self.risk_reward_ratio * (1 + (signal_strength / 100))
            else:
                dynamic_rr_ratio = 1

            signals['take_profit'] = (
                signals['entry_price'] - 
                (signals['stop_loss'] - signals['entry_price']) * dynamic_rr_ratio
            )
            
            signals['position_size'] = self.calculate_position_size(signals['entry_price'])

        return signals
    
    def backtest(self, data):
        initial_capital = self.capital
        portfolio_value = initial_capital
        trades = []
        current_position = None
        total_profit_account = 0
        total_days_in_long = 0
        total_days_in_short = 0
        
        for i in range(10, len(data)):
            current_data = data.iloc[:i] 
            signals = self.generate_trade_signals(current_data)
            current_row = data.iloc[i]
            current_date = current_row.name

            if not current_position:
                if signals['long_condition']:
                    current_position = {
                        'type': 'long',
                        'entry': signals['entry_price'],
                        'stop_loss': signals['stop_loss'],
                        'take_profit': signals['take_profit'],
                        'size': signals['position_size'],
                        'entry_date': current_date
                    }
                    print(f"New long position: Entry={signals['entry_price']}, Stop Loss={signals['stop_loss']}, Take Profit={signals['take_profit']}, Position Size={signals['position_size']}")
                elif signals['short_condition']:
                    current_position = {
                        'type': 'short',
                        'entry': signals['entry_price'],
                        'stop_loss': signals['stop_loss'],
                        'take_profit': signals['take_profit'],
                        'size': signals['position_size'],
                        'entry_date': current_date
                    }
                    print(f"New short position: Entry={signals['entry_price']}, Stop Loss={signals['stop_loss']}, Take Profit={signals['take_profit']}, Position Size={signals['position_size']}")
            
            if current_position:
                if current_position['type'] == 'long':
                    if (current_row['Low'] <= current_position['stop_loss'] or 
                        current_row['High'] >= current_position['take_profit']):
                        
                        duration_days = (current_date - current_position['entry_date']).days
                        total_days_in_long += duration_days

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
                            'result': trade_result,
                            'duration_days': duration_days,
                            'entry_date': current_position['entry_date'],
                            'exit_date': current_date
                        })
                        
                        print(f"Trade closed: Type=Long, Entry={current_position['entry']}, Exit={exit_price}, Profit={profit_account}, Result={trade_result}, Duration={duration_days} days")
                        
                        self.capital = portfolio_value
                        current_position = None
                
                elif current_position['type'] == 'short':
                    if (current_row['High'] >= current_position['stop_loss'] or 
                        current_row['Low'] <= current_position['take_profit']):
                        
                        # Calculate trade duration
                        duration_days = (current_date - current_position['entry_date']).days
                        total_days_in_short += duration_days

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
                            'result': trade_result,
                            'duration_days': duration_days,
                            'entry_date': current_position['entry_date'],
                            'exit_date': current_date
                        })
                        
                        print(f"Trade closed: Type=Short, Entry={current_position['entry']}, Exit={exit_price}, Profit={profit_account}, Result={trade_result}, Duration={duration_days} days")
                        
                        self.capital = portfolio_value
                        current_position = None
            
        total_return = (portfolio_value - initial_capital) / initial_capital * 100
        profitable_trades = [trade for trade in trades if trade['result'] == 'profit']
        losing_trades = [trade for trade in trades if trade['result'] == 'loss']
        
        # Calculate average duration for all trades
        avg_duration = sum(trade['duration_days'] for trade in trades) / len(trades) if trades else 0
        
        # Calculate average duration separately for long and short trades
        long_trades = [trade for trade in trades if trade['type'] == 'long']
        short_trades = [trade for trade in trades if trade['type'] == 'short']
        avg_duration_long = sum(trade['duration_days'] for trade in long_trades) / len(long_trades) if long_trades else 0
        avg_duration_short = sum(trade['duration_days'] for trade in short_trades) / len(short_trades) if short_trades else 0
        
        return {
            'total_return_percentage': round(total_return, 2),
            'total_trades': len(trades),
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(profitable_trades) / len(trades) * 100, 2) if trades else 0,
            'total_profit': round(total_profit_account, 2),
            'average_profit_per_trade': round(total_profit_account / len(trades), 2) if trades else 0,
            'final_portfolio_value': round(portfolio_value, 2),
            'average_trade_duration': round(avg_duration, 2),
            'average_long_trade_duration': round(avg_duration_long, 2),
            'average_short_trade_duration': round(avg_duration_short, 2),
            'total_days_in_long': total_days_in_long,
            'total_days_in_short': total_days_in_short
        }
    
    def run(self):     
        while True:
            try:
                historical_data = self.fetch_historical_data()
                if historical_data is not None:
                    # performance = self.backtest(historical_data)
                    # self.logger.info(f"Strategy Performance: {performance}")

                    data = self.getTrades()
                    if not data.get('status', False):
                        raise ValueError("API returned status=False")
                    active_trades = data.get('returnData', {})
                    has_current_symbol_active_trade = False
                    for active_trade in active_trades:
                        if active_trade['symbol'] == self.symbol:
                            has_current_symbol_active_trade = True
                    
                    if not has_current_symbol_active_trade:
                        latest_signals = self.generate_trade_signals(historical_data)
                        if latest_signals['long_condition']:
                            # Execute a buy (long) trade
                            self.execute_trade_transaction(
                                cmd=0,
                                stop_loss=latest_signals['stop_loss'],
                                take_profit=latest_signals['take_profit'],
                                volume=self.trade_volume
                            )
                            self.logger.info(f"LONG SIGNAL: {latest_signals['long_condition']}")

                        elif latest_signals['short_condition']:
                            # Execute a sell (short) trade
                            self.execute_trade_transaction(
                                cmd=1,
                                stop_loss=latest_signals['stop_loss'],
                                take_profit=latest_signals['take_profit'],
                                volume=self.trade_volume
                            )
                            self.logger.info(f"SHORT SIGNAL: {latest_signals['short_condition']}")
                time.sleep(self.run_interval)

            except Exception as e:
                self.logger.error(f"Trading strategy error: {e}")
                time.sleep(self.run_interval)

def main():
    XTB_USER_ID = os.getenv('XTB_USER_ID')
    XTB_PASSWORD = os.getenv('XTB_PASSWORD')

    strategy_gold = XAUUSDTradingStrategy(
        xtb_user_id=XTB_USER_ID,
        xtb_password=XTB_PASSWORD,
        pip_value = 0.01,
        trade_volume = 0.01,
        symbol='GOLD',
        use_dynamic_rr=True,
        timeframe=30,
        chart_start_from=1717711200000,
        run_interval=1800
    )

    strategy_us500 = XAUUSDTradingStrategy(
        xtb_user_id=XTB_USER_ID,
        xtb_password=XTB_PASSWORD,
        pip_value = 0.1,
        trade_volume = 0.01,
        symbol='US500',
        use_dynamic_rr=False,
        timeframe=240,
        chart_start_from=1517711200000,
        run_interval=1800
    )

    thread_gold = threading.Thread(target=strategy_gold.run)
    thread_us500 = threading.Thread(target=strategy_us500.run)

    thread_gold.start()
    thread_us500.start()

if __name__ == "__main__":
    main()
