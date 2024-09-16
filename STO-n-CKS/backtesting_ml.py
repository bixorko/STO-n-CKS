import pandas as pd
import time


def backtest_ml_strategy_without_sentiment(data, model, initial_cash=1000.0):
    X = data[['SMA50', 'SMA200', 'ATR', 'Volatility', 'Momentum', 'Lag_1', 'Lag_2', 'Lag_3', 'Lag_4', 'Lag_5']]
    predictions = model.predict(X)
    
    cash = initial_cash
    position = 0
    portfolio_value = []
    
    for i in range(len(data)):
        if predictions[i] == 1 and position == 0:  # Buy signal
            position = cash // data['Close'].iloc[i]
            cash -= position * data['Close'].iloc[i]
            print(f"Bought {position} units at {data['Close'].iloc[i]} on {data.index[i]}")
        
        elif predictions[i] == 0 and position > 0:  # Sell signal
            cash += position * data['Close'].iloc[i]
            print(f"Sold {position} units at {data['Close'].iloc[i]} on {data.index[i]}")
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


def backtest_ml_strategy_with_sentiment(data, model, ticker, finnhub_client, sia, initial_cash=1000.0):
    X = data[['SMA50', 'SMA200', 'ATR', 'Volatility', 'Momentum', 'Lag_1', 'Lag_2', 'Lag_3', 'Lag_4', 'Lag_5']]
    predictions = model.predict(X)
    
    cash = initial_cash
    position = 0
    portfolio_value = []
    
    for i in range(len(data)):
        date = data.index[i].strftime('%Y-%m-%d')
        sentiment = get_sentiment(ticker, date, finnhub_client, sia)
        
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


def get_sentiment(ticker, date, finnhub_client, sia):
    news = finnhub_client.company_news(ticker, _from=date, to=date)
    time.sleep(1)  # Implement rate limiting by sleeping for 1 second
    
    if not news:
        return 0.0
    
    sentiment_score = 0
    for article in news:
        sentiment_score += sia.polarity_scores(article['headline'])['compound']
    
    sentiment_score /= len(news)
    
    return sentiment_score
