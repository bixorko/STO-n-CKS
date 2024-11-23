import numpy as np
import pandas as pd
import yfinance as yf
import discord
import asyncio
import os

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

# Initialize the stock data for live trading
async def monitor_stock():
    while True:
        try:
            # Fetch the latest stock data
            stock_data = yf.download(ticker, period='30d', interval='1d')

            # Skip iteration if not enough data is available
            if len(stock_data) < 30:
                await asyncio.sleep(86400)  # Retry next day
                continue

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

                    # Generate stop-loss and take-profit levels
                    if not pd.isna(stock_data['ATR'].iloc[i]):
                        stop_loss = stock_data['Close'].iloc[i] + (atr_multiplier_stop_loss * stock_data['ATR'].iloc[i])
                        take_profit = stock_data['Close'].iloc[i] + (atr_multiplier_take_profit * stock_data['ATR'].iloc[i])

                        # Send signal through Discord
                        await send_discord_signal(stock_data.index[i].strftime('%Y-%m-%d'), stock_data['Close'].iloc[i], take_profit, stop_loss)

            # Wait until the next day to re-evaluate
            await asyncio.sleep(86400)
        except Exception as e:
            print(f"An error occurred: {e}")
            await asyncio.sleep(3600)  # Retry after 1 hour

# Function to send a signal to Discord
async def send_discord_signal(date, price, take_profit, stop_loss):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        message = f"**Stock Signal Alert** 🚀\n\n**Stock:** {ticker} 🌟\n**Date:** {date}\n**Price:** ${price:.2f} 💸\n**Take Profit (TP):** ${take_profit:.2f} 🍋\n**Stop Loss (SL):** ${stop_loss:.2f} ⚠️"
        await channel.send(message)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    client.loop.create_task(monitor_stock())

client.run(DISCORD_TOKEN)