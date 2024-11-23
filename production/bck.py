import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# Constants
ticker = 'NVDA'
start_date = '2022-01-01'
end_date = '2024-11-22'
atr_window = 14
atr_multiplier_stop_loss = -0.5
atr_multiplier_take_profit = 1.5

# Initialize an empty DataFrame to store results
cumulative_results = pd.DataFrame()

# Iterate day by day to simulate real trading conditions
current_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

while current_date <= end_date:
    # Fetch data up to the current date
    stock_data = yf.download(ticker, start=start_date, end=current_date.strftime('%Y-%m-%d'))

    # Skip iteration if not enough data is available
    if len(stock_data) < 30:
        current_date += pd.Timedelta(days=1)
        continue

    # Initialize new columns for True Range (TR), ATR, Moving Averages, and derivatives
    stock_data['TR'] = np.nan
    stock_data['ATR'] = np.nan
    stock_data['30_MA'] = np.nan
    stock_data['First_Derivative'] = np.nan
    stock_data['Second_Derivative'] = np.nan
    stock_data['Signal'] = None
    stock_data['Position'] = 0
    stock_data['ATR_Stop_Loss'] = np.nan
    stock_data['ATR_Take_Profit'] = np.nan
    stock_data['Strategy_Return'] = 0.0

    # Iterate through the available data up to the current date
    for i in range(1, len(stock_data)):
        # Calculate True Range (TR)
        high_low = stock_data['High'].iloc[i] - stock_data['Low'].iloc[i]
        high_close = abs(stock_data['High'].iloc[i] - stock_data['Close'].iloc[i - 1])
        low_close = abs(stock_data['Low'].iloc[i] - stock_data['Close'].iloc[i - 1])
        stock_data.at[stock_data.index[i], 'TR'] = max(high_low, high_close, low_close)

        # Calculate ATR with a 14-day rolling window, starting after enough data is available
        if i >= atr_window:
            stock_data.at[stock_data.index[i], 'ATR'] = stock_data['TR'].iloc[i - atr_window + 1:i + 1].mean()

        # Calculate the 30-day moving average and its derivatives
        if i >= 29:
            stock_data.at[stock_data.index[i], '30_MA'] = stock_data['Close'].iloc[i - 29:i + 1].mean()
            stock_data.at[stock_data.index[i], 'First_Derivative'] = stock_data['30_MA'].iloc[i] - stock_data['30_MA'].iloc[i - 1]
            if i >= 30:
                stock_data.at[stock_data.index[i], 'Second_Derivative'] = stock_data['First_Derivative'].iloc[i] - stock_data['First_Derivative'].iloc[i - 1]

        # Generate buy signals based on concavity changes
        if (stock_data['Second_Derivative'].iloc[i] > 0) and (stock_data['First_Derivative'].iloc[i] > 0):
            stock_data.at[stock_data.index[i], 'Signal'] = 'Buy'

        # Determine position
        stock_data.at[stock_data.index[i], 'Position'] = 1 if stock_data['Signal'].iloc[i - 1] == 'Buy' else stock_data['Position'].iloc[i - 1]

        # Calculate ATR-based stop-loss and take-profit levels
        if not pd.isna(stock_data['ATR'].iloc[i - 1]):
            stock_data.at[stock_data.index[i], 'ATR_Stop_Loss'] = stock_data['Close'].iloc[i - 1] + (atr_multiplier_stop_loss * stock_data['ATR'].iloc[i - 1])
            stock_data.at[stock_data.index[i], 'ATR_Take_Profit'] = stock_data['Close'].iloc[i - 1] + (atr_multiplier_take_profit * stock_data['ATR'].iloc[i - 1])

        # Calculate daily return
        daily_return = (stock_data['Close'].iloc[i] / stock_data['Close'].iloc[i - 1]) - 1
        stock_data.at[stock_data.index[i], 'Daily_Return'] = daily_return

        # Calculate strategy return
        if stock_data['Position'].iloc[i] == 1:
            if stock_data['Low'].iloc[i] <= stock_data['ATR_Stop_Loss'].iloc[i]:
                stock_data.at[stock_data.index[i], 'Strategy_Return'] = (stock_data['ATR_Stop_Loss'].iloc[i] / stock_data['Close'].iloc[i - 1]) - 1
            elif stock_data['High'].iloc[i] >= stock_data['ATR_Take_Profit'].iloc[i]:
                stock_data.at[stock_data.index[i], 'Strategy_Return'] = (stock_data['ATR_Take_Profit'].iloc[i] / stock_data['Close'].iloc[i - 1]) - 1
            else:
                stock_data.at[stock_data.index[i], 'Strategy_Return'] = daily_return
        else:
            stock_data.at[stock_data.index[i], 'Strategy_Return'] = 0.0

    # Calculate cumulative returns
    stock_data['Cumulative_Market_Return'] = (1 + stock_data['Daily_Return']).cumprod()
    stock_data['Cumulative_Strategy_Return'] = (1 + stock_data['Strategy_Return']).cumprod()

    # Store the last row of the current simulation
    cumulative_results = pd.concat([cumulative_results, stock_data.iloc[[-1]]])

    # Move to the next day
    current_date += pd.Timedelta(days=1)

# Plot cumulative returns
plt.figure(figsize=(14, 8))
plt.plot(cumulative_results.index, cumulative_results['Cumulative_Market_Return'], label='Market Return', color='blue', linewidth=2)
plt.plot(cumulative_results.index, cumulative_results['Cumulative_Strategy_Return'], label='Strategy Return', color='green', linewidth=2)
plt.title('Cumulative Market Return vs. Strategy Return (Day-by-Day Backtest with ATR-Based Stop-Loss/Take-Profit)')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
plt.grid()
plt.show()