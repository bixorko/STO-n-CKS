import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# Constants
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'BRK-B', 'META', 'UNH', 'V',
           'XOM', 'JNJ', 'WMT', 'JPM', 'MA', 'PG', 'LLY', 'CVX', 'HD', 'MRK',
           'KO', 'PEP', 'ABBV', 'COST', 'AVGO', 'MCD', 'CSCO', 'ADBE', 'VZ', 'NFLX',
           'PFE', 'INTC', 'TMO', 'ABT', 'DIS', 'CRM', 'NKE', 'WFC', 'ACN', 'DHR',
           'LIN', 'TXN', 'NEE', 'TMUS', 'PM', 'RTX', 'MS', 'AMD', 'LOW', 'SCHW',
           'ELV', 'ORCL', 'AMT', 'UPS', 'CVS', 'GS', 'HON', 'BMY', 'IBM', 'SBUX',
           'MDT', 'INTU', 'BLK', 'T', 'CAT', 'DE', 'AMGN', 'SPGI', 'PLD', 'BA',
           'C', 'SYK', 'MO', 'ADP', 'BKNG', 'GE', 'ISRG', 'ZTS', 'NOW', 'SO',
           'CB', 'MDLZ', 'TGT', 'PNC', 'ADI', 'USB', 'MMM', 'CCI', 'DUK', 'GM',
           'MU', 'BDX', 'NSC', 'EQIX', 'APD', 'COP', 'ICE', 'SCHW']

# Constants
start_date = '2022-01-01'
end_date = '2024-11-22'
atr_window = 14
atr_multiplier_stop_loss = -0.5
atr_multiplier_take_profit = 1.5

# Initialize a dictionary to store final results
final_results = {}

# Iterate over each ticker
ticker_counter = 1
for ticker in tickers:
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
                stock_data.at[stock_data.index[i], 'ATR'] = stock_data['TR'].iloc[i - atr_window:i + 1].mean()

            # Calculate the 30-day moving average and its derivatives
            if i >= 29:
                stock_data.at[stock_data.index[i], '30_MA'] = stock_data['Close'].iloc[i - 29:i + 1].mean()
                stock_data.at[stock_data.index[i], 'First_Derivative'] = stock_data['30_MA'].iloc[i] - stock_data['30_MA'].iloc[i - 1]
                if i >= 30:
                    stock_data.at[stock_data.index[i], 'Second_Derivative'] = stock_data['First_Derivative'].iloc[i] - stock_data['First_Derivative'].iloc[i - 1]

            # Generate buy signals based on concavity changes
            if (stock_data['Second_Derivative'].iloc[i] > 0) and (stock_data['First_Derivative'].iloc[i] > 0):
                stock_data.at[stock_data.index[i], 'Signal'] = 'Buy'

        # Start trading on the next day using signals calculated until day i
        for i in range(1, len(stock_data) - 1):
            # Determine position based on previous day's signal
            stock_data.at[stock_data.index[i + 1], 'Position'] = 1 if stock_data['Signal'].iloc[i] == 'Buy' else stock_data['Position'].iloc[i]

            # Calculate ATR-based stop-loss and take-profit levels (for the next day)
            if not pd.isna(stock_data['ATR'].iloc[i]):
                stock_data.at[stock_data.index[i + 1], 'ATR_Stop_Loss'] = stock_data['Open'].iloc[i + 1] + (atr_multiplier_stop_loss * stock_data['ATR'].iloc[i])
                stock_data.at[stock_data.index[i + 1], 'ATR_Take_Profit'] = stock_data['Open'].iloc[i + 1] + (atr_multiplier_take_profit * stock_data['ATR'].iloc[i])

            # Calculate strategy return based on next day's open price
            if stock_data['Position'].iloc[i + 1] == 1:
                if stock_data['Low'].iloc[i + 1] <= stock_data['ATR_Stop_Loss'].iloc[i + 1]:
                    stock_data.at[stock_data.index[i + 1], 'Strategy_Return'] = (stock_data['ATR_Stop_Loss'].iloc[i + 1] / stock_data['Open'].iloc[i + 1]) - 1
                elif stock_data['High'].iloc[i + 1] >= stock_data['ATR_Take_Profit'].iloc[i + 1]:
                    stock_data.at[stock_data.index[i + 1], 'Strategy_Return'] = (stock_data['ATR_Take_Profit'].iloc[i + 1] / stock_data['Open'].iloc[i + 1]) - 1
                else:
                    stock_data.at[stock_data.index[i + 1], 'Strategy_Return'] = (stock_data['Close'].iloc[i + 1] / stock_data['Open'].iloc[i + 1]) - 1
            else:
                stock_data.at[stock_data.index[i + 1], 'Strategy_Return'] = 0.0

        # Calculate cumulative returns
        stock_data['Daily_Return'] = stock_data['Close'].pct_change()
        stock_data['Cumulative_Market_Return'] = (1 + stock_data['Daily_Return']).cumprod()
        stock_data['Cumulative_Strategy_Return'] = (1 + stock_data['Strategy_Return']).cumprod()

        # Store the last row of the current simulation
        cumulative_results = pd.concat([cumulative_results, stock_data.iloc[[-1]]])

        # Move to the next day
        current_date += pd.Timedelta(days=1)

    # Store the final cumulative return for each stock
    final_market_return = cumulative_results['Cumulative_Market_Return'].iloc[-1]
    final_strategy_return = cumulative_results['Cumulative_Strategy_Return'].iloc[-1]
    difference = (final_strategy_return - final_market_return) * 100
    final_results[ticker] = {'Market Return (%)': final_market_return * 100, 'Strategy Return (%)': final_strategy_return * 100, 'Difference (%)': difference}

    # Plot the cumulative returns for market and strategy
    plt.figure(figsize=(10, 6))
    plt.plot(stock_data.index, stock_data['Cumulative_Market_Return'], label='Market Return', linestyle='-', linewidth=2)
    plt.plot(stock_data.index, stock_data['Cumulative_Strategy_Return'], label='Strategy Return', linestyle='--', linewidth=2)
    plt.title(f"Cumulative Returns for {ticker}")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.legend()
    plt.grid()
    plt.tight_layout()

    # Save the plot as an image file
    plot_filename = f"{ticker}_cumulative_returns.png"
    plt.savefig(plot_filename)
    plt.close()
