import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
import finnhub
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import time

nltk.download('vader_lexicon')

# Initialize the Finnhub client
finnhub_client = finnhub.Client(api_key="cm62s09r01qg94ptj040cm62s09r01qg94ptj04g")

# Initialize NLTK's sentiment analyzer
sia = SentimentIntensityAnalyzer()

# Step 1: Data Retrieval
def get_data(ticker, start, end, interval):
    data = yf.download(ticker, start=start, end=end, interval=interval)
    if data.empty:
        print(f"No data found for {ticker} with interval {interval} from {start} to {end}.")
    return data

# Feature Engineering
def add_features(data):
    data['SMA50'] = data['Close'].rolling(window=50).mean()
    data['SMA200'] = data['Close'].rolling(window=200).mean()
    data['ATR'] = data['High'].rolling(window=14).max() - data['Low'].rolling(window=14).min()
    data['Returns'] = data['Close'].pct_change()
    data['Volatility'] = data['Returns'].rolling(window=10).std()
    data['Momentum'] = data['Close'].diff(5)
    
    # Lagged features
    for lag in range(1, 6):
        data[f'Lag_{lag}'] = data['Returns'].shift(lag)
    
    # Drop NaN values
    data.dropna(inplace=True)
    
    return data

# Prepare data for machine learning
def prepare_ml_data(data):
    X = data[['SMA50', 'SMA200', 'ATR', 'Volatility', 'Momentum', 'Lag_1', 'Lag_2', 'Lag_3', 'Lag_4', 'Lag_5']]
    y = np.where(data['Returns'].shift(-1) > 0, 1, 0)  # Predict next day's return direction
    
    return X, y

# Model Training
def train_model(X, y):
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    return model

# Sentiment Analysis for confirmation with rate limiting
def get_sentiment(ticker, date):
    # Fetch news from Finnhub for the specified date
    news = finnhub_client.company_news(ticker, _from=date, to=date)
    
    # Implement rate limiting by sleeping for 1 second after each API call
    time.sleep(1)  # 1 second to keep within the 60 calls per minute limit
    
    # If no news available, return neutral sentiment
    if not news:
        return 0.0
    
    # Aggregate sentiment scores
    sentiment_score = 0
    for article in news:
        sentiment_score += sia.polarity_scores(article['headline'])['compound']
    
    # Average sentiment score
    sentiment_score /= len(news)
    
    return sentiment_score

# Backtesting with Machine Learning Strategy and Sentiment Confirmation
def backtest_ml_strategy(data, model, ticker, initial_cash=1000.0):
    X = data[['SMA50', 'SMA200', 'ATR', 'Volatility', 'Momentum', 'Lag_1', 'Lag_2', 'Lag_3', 'Lag_4', 'Lag_5']]
    predictions = model.predict(X)
    
    cash = initial_cash
    position = 0
    portfolio_value = []
    
    for i in range(len(data)):
        date = data.index[i].strftime('%Y-%m-%d')
        sentiment = get_sentiment(ticker, date)
        
        if predictions[i] == 1 and position == 0 and sentiment > 0:  # Buy signal with positive sentiment
            position = cash // data['Close'].iloc[i]
            cash -= position * data['Close'].iloc[i]
            print(f"Bought {position} units at {data['Close'].iloc[i]} on {data.index[i]} with sentiment {sentiment}")
        
        elif predictions[i] == 0 and position > 0 and sentiment < 0:  # Sell signal with negative sentiment
            cash += position * data['Close'].iloc[i]
            print(f"Sold {position} units at {data['Close'].iloc[i]} on {data.index[i]} with sentiment {sentiment}")
            position = 0
        
        portfolio_value.append(cash + position * data['Close'].iloc[i])
    
    # Final portfolio value
    if position > 0:
        cash += position * data['Close'].iloc[-1]
        portfolio_value[-1] = cash  # Adjust the last portfolio value with final cash
        print(f"Final sale at {data['Close'].iloc[-1]} on {data.index[-1]}")
        position = 0
    
    print(f"Final Portfolio Value: {cash}")
    
    return pd.Series(portfolio_value, index=data.index[:len(portfolio_value)])

# List of popular stock tickers
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']

# Dictionary to hold portfolio values for each stock
portfolio_values = {}

# Execute the Strategy for each stock
for ticker in tickers:
    print(f"Processing {ticker}...")

    # Train on 2023 data
    train_data = get_data(ticker, '2023-01-01', '2024-01-01', '1h')
    train_data = add_features(train_data)
    X_train, y_train = prepare_ml_data(train_data)
    model = train_model(X_train, y_train)

    # Backtest on 2024 data
    test_data = get_data(ticker, '2024-01-01', '2024-08-01', '1h')
    test_data = add_features(test_data)
    portfolio_value = backtest_ml_strategy(test_data, model, ticker)
    
    # Store the results
    portfolio_values[ticker] = portfolio_value

# Convert the portfolio values into a DataFrame for easier comparison
portfolio_df = pd.DataFrame(portfolio_values)

# Plot the portfolio values
plt.figure(figsize=(14, 8))
for ticker in tickers:
    plt.plot(portfolio_df.index, portfolio_df[ticker], label=ticker)

plt.title('Portfolio Value Over Time')
plt.xlabel('Date')
plt.ylabel('Portfolio Value')
plt.legend()
plt.grid(True)
plt.show()

# Display the final portfolio values
print(portfolio_df)

# Results:
    # Without sentiment:
        # Datetime                   AAPL         MSFT         GOOGL         AMZN        TSLA         NVDA
        # 2024-07-31 15:30:00-04:00  1137.766754  1003.001587  1207.549164   909.328079  1337.913132  1662.035980

    # With sentiment
        # 2024-07-31 15:30:00-04:00  1142.331543   981.039978  1133.355988  1069.250031  1296.253891  ????