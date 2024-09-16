import yfinance as yf
import requests
import csv
from nltk.sentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta
import time
import nltk
nltk.download('vader_lexicon')

class StockTrader:
    BUY_THRESHOLD = 0.1
    SELL_THRESHOLD = -0.1
    TRADING_FEE = 1

    def __init__(self, symbol):
        self.symbol = symbol
        self.owned = False
        self.sentiment = 0
        self.article_count = 0
        self.buy_price = None
        self.profit = 0

    def get_news(self, api_key, date):
        url = f"https://finnhub.io/api/v1/company-news?symbol={self.symbol}&from={date.strftime('%Y-%m-%d')}&to={date.strftime('%Y-%m-%d')}&token={api_key}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching news for {self.symbol}: {e}")
            return []

    def get_price(self, date, price_type='Open'):
        stock_info = yf.Ticker(self.symbol)
        try:
            hist = stock_info.history(start=date, end=date + timedelta(days=1))
            if not hist.empty:
                return hist.iloc[0][price_type]
        except Exception as e:
            print(f"Error fetching price for {self.symbol}: {e}")
        return None

    def analyze_sentiment(self, news_data):
        sia = SentimentIntensityAnalyzer()
        total_sentiment = 0
        for article in news_data:
            headline = article['headline']
            sentiment_score = sia.polarity_scores(headline)['compound']
            total_sentiment += sentiment_score
        return total_sentiment

    def simulate_trading(self, csv_file_name, date):
        with open(csv_file_name, 'a', newline='') as file:
            writer = csv.writer(file)
            overall_sentiment = self.sentiment
            action = None
            open_price = self.get_price(date)

            if open_price:
                if overall_sentiment > self.BUY_THRESHOLD and not self.owned:
                    action = "BUY"
                    self.owned = True
                    self.buy_price = open_price
                elif overall_sentiment < self.SELL_THRESHOLD and self.owned:
                    action = "SELL"
                    self.owned = False
                    sell_price = open_price
                    profit = sell_price - self.buy_price - self.TRADING_FEE
                    self.profit += profit

            writer.writerow([
                self.symbol, 
                open_price if open_price else "N/A", 
                action if action else "NO ACTION", 
                date.strftime('%Y-%m-%d'), 
                overall_sentiment, 
                self.article_count, 
                self.profit
            ])

if __name__ == "__main__":
    stock_symbols = ['TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN']

    traders = [StockTrader(symbol) for symbol in stock_symbols]
    api_key = 'cm62s09r01qg94ptj040cm62s09r01qg94ptj04g'

    start_date = datetime(2023, 1, 1)
    current_date = datetime.now()

    while start_date <= current_date:
        for trader in traders:
            news_data = trader.get_news(api_key, start_date)
            sentiment_score = trader.analyze_sentiment(news_data)
            trader.sentiment = sentiment_score
            trader.article_count = len(news_data)
            time.sleep(2)
        
        for trader in traders:
            trader.simulate_trading('trading_simulation.csv', start_date)
        
        start_date += timedelta(days=1)
