import random
import pandas as pd
import yfinance as yf

def get_nasdaq100_stocks():
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    tables = pd.read_html(url)
    
    possible_columns = ['Ticker', 'Symbol', 'Ticker symbol', 'Stock symbol']
    
    for table in tables:
        for col in possible_columns:
            if col in table.columns:
                return table[col].tolist()
    
    raise ValueError("Could not find NASDAQ-100 stock tickers in Wikipedia tables")

def get_random_stock_info():
    try:
        nasdaq_stocks = get_nasdaq100_stocks()
        
        random_ticker = random.choice(nasdaq_stocks)
        
        stock = yf.Ticker(random_ticker)
        stock_info = stock.info
        
        info = {
            'Name': f"{random_ticker} - {stock_info.get('shortName', 'N/A')}",
            'Symbol': random_ticker
        }
        
        return info
        
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

if __name__ == "__main__":
    stock_info = get_random_stock_info()
    
    if stock_info:
        for key, value in stock_info.items():
            print(f"{key}: {value}")