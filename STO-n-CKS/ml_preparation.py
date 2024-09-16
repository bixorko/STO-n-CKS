import numpy as np

def prepare_ml_data(data):
    X = data[['SMA50', 'SMA200', 'ATR', 'Volatility', 'Momentum', 'Lag_1', 'Lag_2', 'Lag_3', 'Lag_4', 'Lag_5']]
    y = np.where(data['Returns'].shift(-1) > 0, 1, 0)  # Predict next day's return direction
    
    return X, y
