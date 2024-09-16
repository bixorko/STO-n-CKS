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
