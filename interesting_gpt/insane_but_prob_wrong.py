import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# Fetch real data using yfinance
ticker = 'NVDA' 
start_date = '2022-01-01'
end_date = '2024-11-11'

# Download historical data
stock_data = yf.download(ticker, start=start_date, end=end_date)

# Calculate the 30-day moving average
stock_data['30_MA'] = stock_data['Close'].rolling(window=30).mean()

# Calculate first and second derivatives using finite differences
stock_data['First_Derivative'] = stock_data['30_MA'].diff()
stock_data['Second_Derivative'] = stock_data['First_Derivative'].diff()

# Generate buy signals based on concavity changes
stock_data['Signal'] = np.where((stock_data['Second_Derivative'] > 0) & (stock_data['First_Derivative'] > 0), 'Buy', None)

# Calculate strategy returns with stop-loss and take-profit
stop_loss = 0.02  # 2% stop loss
take_profit = 0.05  # 5% take profit

stock_data['Position'] = stock_data['Signal'].replace({'Buy': 1}).ffill().fillna(0)
stock_data['Shifted_Position'] = stock_data['Position'].shift()
stock_data['Daily_Return'] = stock_data['Close'].pct_change()

stock_data['Strategy_Return'] = 0
for i in range(1, len(stock_data)):
    if stock_data['Shifted_Position'].iloc[i] == 1:  # Buy position
        change = (stock_data['Close'].iloc[i] - stock_data['Close'].iloc[i - 1]) / stock_data['Close'].iloc[i - 1]
        if change <= -stop_loss:
            stock_data['Strategy_Return'].iloc[i] = -stop_loss  # Stop-loss
            stock_data['Shifted_Position'].iloc[i] = 0
        elif change >= take_profit:
            stock_data['Strategy_Return'].iloc[i] = take_profit  # Take-profit
            stock_data['Shifted_Position'].iloc[i] = 0
        else:
            stock_data['Strategy_Return'].iloc[i] = stock_data['Daily_Return'].iloc[i]

# Calculate cumulative returns
stock_data['Cumulative_Market_Return'] = (1 + stock_data['Daily_Return']).cumprod()
stock_data['Cumulative_Strategy_Return'] = (1 + stock_data['Strategy_Return']).cumprod()

# Plot cumulative returns
plt.figure(figsize=(14, 8))
plt.plot(stock_data.index, stock_data['Cumulative_Market_Return'], label='Market Return', color='blue', linewidth=2)
plt.plot(stock_data.index, stock_data['Cumulative_Strategy_Return'], label='Strategy Return', color='green', linewidth=2)
plt.title('Cumulative Market Return vs. Strategy Return')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
plt.grid()
plt.show()
