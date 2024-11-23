import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# Fetch real data using yfinance
ticker = 'NVDA' 
start_date = '2022-01-01'
end_date = '2024-11-22'

# Download historical data
stock_data = yf.download(ticker, start=start_date, end=end_date)

# Initialize columns for the backtest
stock_data['30_MA'] = np.nan
stock_data['First_Derivative'] = np.nan
stock_data['Second_Derivative'] = np.nan
stock_data['Signal'] = None
stock_data['Position'] = 0
stock_data['Strategy_Return'] = 0

# Set stop-loss and take-profit levels
stop_loss = 0.02  # 2% stop loss
take_profit = 0.05  # 5% take profit

# Iterate over each day, starting from the 30th day to ensure we have enough data for the moving average
for i in range(30, len(stock_data)):
    # Calculate the 30-day moving average for the current day
    stock_data['30_MA'].iloc[i] = stock_data['Close'].iloc[i-29:i+1].mean()
    
    # Calculate first and second derivatives using finite differences
    stock_data['First_Derivative'].iloc[i] = stock_data['30_MA'].iloc[i] - stock_data['30_MA'].iloc[i-1]
    stock_data['Second_Derivative'].iloc[i] = stock_data['First_Derivative'].iloc[i] - stock_data['First_Derivative'].iloc[i-1]
    
    # Generate buy signals based on concavity changes
    if stock_data['Second_Derivative'].iloc[i] > 0 and stock_data['First_Derivative'].iloc[i] > 0:
        stock_data['Signal'].iloc[i] = 'Buy'
    
    # Determine position based on the signal
    if stock_data['Signal'].iloc[i] == 'Buy':
        stock_data['Position'].iloc[i] = 1
    else:
        stock_data['Position'].iloc[i] = stock_data['Position'].iloc[i-1]
    
    # Calculate strategy return with stop-loss and take-profit
    if stock_data['Position'].iloc[i-1] == 1:  # If we were holding a position
        change = (stock_data['Close'].iloc[i] - stock_data['Close'].iloc[i - 1]) / stock_data['Close'].iloc[i - 1]
        if change <= -stop_loss:
            stock_data['Strategy_Return'].iloc[i] = -stop_loss  # Stop-loss triggered
            stock_data['Position'].iloc[i] = 0  # Close position
        elif change >= take_profit:
            stock_data['Strategy_Return'].iloc[i] = take_profit  # Take-profit triggered
            stock_data['Position'].iloc[i] = 0  # Close position
        else:
            stock_data['Strategy_Return'].iloc[i] = change  # Daily return
    else:
        stock_data['Strategy_Return'].iloc[i] = 0

# Calculate daily market return
stock_data['Daily_Return'] = stock_data['Close'].pct_change()

# Calculate cumulative returns
stock_data['Cumulative_Market_Return'] = (1 + stock_data['Daily_Return']).cumprod()
stock_data['Cumulative_Strategy_Return'] = (1 + stock_data['Strategy_Return']).cumprod()

# Plot cumulative returns
plt.figure(figsize=(14, 8))
plt.plot(stock_data.index, stock_data['Cumulative_Market_Return'], label='Market Return', color='blue', linewidth=2)
plt.plot(stock_data.index, stock_data['Cumulative_Strategy_Return'], label='Strategy Return', color='green', linewidth=2)
plt.title('Cumulative Market Return vs. Strategy Return (Day-by-Day Backtest)')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
plt.grid()
plt.show()
