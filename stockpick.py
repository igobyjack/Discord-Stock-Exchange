import random
import pandas as pd
import yfinance as yf

def get_sp500_stocks():
    """Get the list of S&P 500 stock tickers from Wikipedia."""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url)
    sp500_table = tables[0]
    return sp500_table['Symbol'].tolist()

def get_random_stock_info():
    """Pick a random stock from S&P 500 and return its information."""
    try:
        # Get S&P 500 stocks
        sp500_stocks = get_sp500_stocks()
        
        # Pick a random stock ticker
        random_ticker = random.choice(sp500_stocks)
        
        # Get stock information using yfinance
        stock = yf.Ticker(random_ticker)
        stock_info = stock.info
        
        # Extract relevant information
        info = {
            'Name': stock_info.get('shortName', 'N/A'),
        }
        
        return info
        
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

if __name__ == "__main__":
    print("Picking a random S&P 500 stock...")
    stock_info = get_random_stock_info()
    
    if stock_info:
        print("\nRandom Stock Information:")
        for key, value in stock_info.items():
            print(f"{key}: {value}")