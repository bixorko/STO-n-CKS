import numpy as np 
import pandas as pd
import yfinance as yf
import discord
import asyncio
import os
import schedule

# Constants
ticker = 'NVDA'
start_date = '2022-01-01'
atr_window = 14
atr_multiplier_stop_loss = -0.5
atr_multiplier_take_profit = 1.5

# Discord bot setup
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
client = discord.Client(intents=discord.Intents.default())

# Function to process stock data and generate signals
def process_stock_data(stock_data):
    # Initialize new columns for True Range (TR), ATR, Moving Averages, and derivatives
    stock_data['TR'] = np.nan
    stock_data['ATR'] = np.nan
    stock_data['30_MA'] = np.nan
    stock_data['First_Derivative'] = np.nan
    stock_data['Second_Derivative'] = np.nan
    stock_data['Signal'] = None
    stock_data['ATR_Stop_Loss'] = np.nan
    stock_data['ATR_Take_Profit'] = np.nan

    # Iterate through the available data
    for i in range(1, len(stock_data) - 1):
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

            # Generate stop-loss and take-profit levels based on the next day's opening price
            if not pd.isna(stock_data['ATR'].iloc[i]) and i + 1 < len(stock_data):
                next_open = stock_data['Open'].iloc[i + 1]
                stop_loss = next_open + (atr_multiplier_stop_loss * stock_data['ATR'].iloc[i])
                take_profit = next_open + (atr_multiplier_take_profit * stock_data['ATR'].iloc[i])

                # Send signal through Discord
                asyncio.create_task(send_discord_signal(stock_data.index[i + 1].strftime('%Y-%m-%d'), next_open, take_profit, stop_loss))

# Initialize the stock data for historical simulation and live trading
async def monitor_stock():
    try:
        # Fetch historical stock data from start_date until now
        stock_data = yf.download(ticker, start=start_date, interval='1d')

        # Process historical data to simulate trading signals
        process_stock_data(stock_data)

        # Enter live monitoring mode
        while True:
            # Fetch the latest stock data for the past month
            live_data = yf.download(ticker, period='1mo', interval='1d')

            # Skip iteration if not enough data is available
            if len(live_data) < 30:
                await asyncio.sleep(86400)  # Retry next day
                continue

            # Process the live data to generate signals
            process_stock_data(live_data)

            # Wait until the next day to re-evaluate
            await asyncio.sleep(86400)
    except Exception as e:
        print(f"An error occurred: {e}")
        await asyncio.sleep(3600)  # Retry after 1 hour

# Function to send a signal to Discord
async def send_discord_signal(date, price, take_profit, stop_loss):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        message = (
            f"```\n"
            f"Stock Signal Alert 🚀\n"
            f"======================\n"
            f"Stock: {ticker} 🌟\n"
            f"Date: {date}\n"
            f"Opening Price: ${price:.2f} 💸\n"
            f"Take Profit (TP): ${take_profit:.2f} 🍋\n"
            f"Stop Loss (SL): ${stop_loss:.2f} ⚠️\n"
            f"======================\n"
            f"```"
        )
        await channel.send(message)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    schedule.every().day.at("09:30").do(lambda: asyncio.create_task(monitor_stock()))  # Assuming market opens at 9:30 AM
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)

client.run(DISCORD_TOKEN)
