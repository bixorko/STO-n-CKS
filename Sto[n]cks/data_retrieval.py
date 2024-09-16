import yfinance as yf

def get_data(ticker, start, end, interval):
    data = yf.download(ticker, start=start, end=end, interval=interval)
    if data.empty:
        print(f"No data found for {ticker} with interval {interval} from {start} to {end}.")
    return data
