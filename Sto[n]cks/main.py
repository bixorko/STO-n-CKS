import pandas as pd
import matplotlib.pyplot as plt
from data_retrieval import get_data
from feature_engineering import add_features
from ml_preparation import prepare_ml_data
from model_training import train_model
from backtesting_ml import backtest_ml_strategy_with_sentiment, backtest_ml_strategy_without_sentiment
import finnhub
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk

# Initialize NLTK's sentiment analyzer and Finnhub client
nltk.download('vader_lexicon')
sia = SentimentIntensityAnalyzer()
finnhub_client = finnhub.Client(api_key="cm62s09r01qg94ptj040cm62s09r01qg94ptj04g")

# Tickers and comparison with YTD data
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', '^GSPC']  # Including S&P 500 (^GSPC)

# Dictionary to hold portfolio values for each stock for both strategies
portfolio_values_ml = {}
portfolio_values_ml_sentiment = {}
ytd_returns = {}

# Execute the Strategy for each stock
for ticker in tickers:
    print(f"Processing {ticker}...")

    # Train on 2023 data
    train_data = get_data(ticker, '2023-01-01', '2024-01-01', '1h')
    train_data = add_features(train_data)
    X_train, y_train = prepare_ml_data(train_data)
    model = train_model(X_train, y_train)

    # Backtest on 2024 data without sentiment analysis
    test_data = get_data(ticker, '2024-01-01', '2024-08-01', '1h')
    test_data = add_features(test_data)
    portfolio_value_ml = backtest_ml_strategy_without_sentiment(test_data, model)
    
    # Backtest on 2024 data with sentiment analysis
    portfolio_value_ml_sentiment = backtest_ml_strategy_with_sentiment(
        test_data, model, ticker, finnhub_client, sia
    )
    
    # Store the results
    portfolio_values_ml[ticker] = portfolio_value_ml
    portfolio_values_ml_sentiment[ticker] = portfolio_value_ml_sentiment

    # Calculate YTD return
    ytd_return = (test_data['Close'].iloc[-1] / test_data['Close'].iloc[0]) - 1
    ytd_returns[ticker] = ytd_return

# Convert the portfolio values into DataFrames for easier comparison
portfolio_df_ml = pd.DataFrame(portfolio_values_ml)
portfolio_df_ml_sentiment = pd.DataFrame(portfolio_values_ml_sentiment)

# Plot the portfolio values
plt.figure(figsize=(14, 8))
for ticker in tickers:
    if ticker != '^GSPC':  # Avoid plotting S&P 500 directly for clarity
        plt.plot(portfolio_df_ml.index, portfolio_df_ml[ticker], label=f"{ticker} ML Strategy")
        plt.plot(portfolio_df_ml_sentiment.index, portfolio_df_ml_sentiment[ticker], label=f"{ticker} ML Strategy with Sentiment", linestyle='--')

plt.title('Portfolio Value Over Time: ML vs ML + Sentiment')
plt.xlabel('Date')
plt.ylabel('Portfolio Value')
plt.legend()
plt.grid(True)
plt.show()

# Plot the YTD performance comparison
ytd_comparison = pd.DataFrame({
    'YTD Return': ytd_returns,
    'Final Portfolio Value (ML)': {ticker: portfolio_df_ml[ticker].iloc[-1] for ticker in tickers},
    'Final Portfolio Value (ML + Sentiment)': {ticker: portfolio_df_ml_sentiment[ticker].iloc[-1] for ticker in tickers}
})

ytd_comparison.plot(kind='bar', figsize=(14, 8))
plt.title('YTD Returns vs Final Portfolio Values')
plt.ylabel('Return / Portfolio Value')
plt.grid(True)
plt.show()

# Display the comparison DataFrame
print("YTD Returns and Final Portfolio Values:")
print(ytd_comparison)
