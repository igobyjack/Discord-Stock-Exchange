import yfinance as yf
import pandas as pd 
import time
import os

# File paths
portfolio_file = 'portfolio.csv'
balance_file = 'balance.csv'

# Initial balance
INITIAL_BALANCE = 50000

def initialize_balance():
    """Initialize the balance file if it doesn't exist"""
    if not os.path.isfile(balance_file):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        df = pd.DataFrame({
            'Timestamp': [timestamp],
            'Balance': [INITIAL_BALANCE],
            'Action': ['Initial deposit'],
            'Amount': [INITIAL_BALANCE]
        })
        df.to_csv(balance_file, index=False)
        return INITIAL_BALANCE
    return get_balance()

def get_balance():
    """Get the current cash balance"""
    if not os.path.isfile(balance_file):
        return initialize_balance()
    
    df = pd.read_csv(balance_file)
    if df.empty:
        return initialize_balance()
    return df['Balance'].iloc[-1]

def update_balance(amount, action):
    """Update the balance after a transaction"""
    current_balance = get_balance()
    new_balance = current_balance - amount
    
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    new_data = pd.DataFrame({
        'Timestamp': [timestamp],
        'Balance': [new_balance],
        'Action': [action],
        'Amount': [amount]
    })
    
    if not os.path.isfile(balance_file):
        new_data.to_csv(balance_file, index=False)
    else:
        new_data.to_csv(balance_file, mode='a', header=False, index=False)
    
    return new_balance

def get_portfolio_value():
    """Calculate total portfolio value (cash + stocks)"""
    # Get cash balance
    cash = get_balance()
    
    # Get stock value
    stock_value = 0
    if os.path.isfile(portfolio_file):
        df = pd.read_csv(portfolio_file)
        if not df.empty:
            for ticker, group in df.groupby('Ticker'):
                shares = group['Shares'].sum()
                try:
                    stock = yf.Ticker(ticker)
                    current_price = stock.history(period='1d')['Close'][0]
                    stock_value += shares * current_price
                except Exception as e:
                    print(f"Error getting price for {ticker}: {str(e)}")
    
    total_value = cash + stock_value
    return {
        'cash': cash,
        'stocks': stock_value,
        'total': total_value
    }

def buy_stock(ticker, amount=None, shares=None):
    try:
        ticker_symbol = ticker.split()[0]
        stock = yf.Ticker(ticker_symbol)
        stock_price = stock.history(period='1d')['Close'][0]
        
        stock_info = stock.info
        company_name = stock_info.get('longName', ticker_symbol)

        # Calculate cost and shares
        if shares is not None:
            shares_to_buy = shares
            cost = shares_to_buy * stock_price
        else:
            shares_to_buy = amount // stock_price
            cost = shares_to_buy * stock_price
        
        # Check if we have enough funds
        current_balance = get_balance()
        if cost > current_balance:
            return False, f"Insufficient funds to buy {company_name} ({ticker_symbol}). Need ${cost:.2f} but only have ${current_balance:.2f}"
        
        # Update the balance
        update_balance(cost, f"Buy {ticker_symbol}")

        print(f"Bought {shares_to_buy} shares of {ticker_symbol} at ${stock_price:.2f} each for a total of ${cost:.2f}")
       
        # Portfolio logging
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        if not os.path.isfile(portfolio_file):
            df = pd.DataFrame(columns=['Timestamp', 'Ticker', 'Name', 'Shares', 'Price', 'Total'])
            df.to_csv(portfolio_file, index=False)
       
        new_data = pd.DataFrame({
            'Timestamp': [timestamp],
            'Ticker': [ticker_symbol],
            'Name': [company_name],
            'Shares': [shares_to_buy],
            'Price': [stock_price],
            'Total': [cost]
        })

        new_data.to_csv(portfolio_file, mode='a', header=False, index=False)

        remaining_balance = current_balance - cost
        return True, f"Bought {shares_to_buy} shares of {company_name} ({ticker_symbol}) at ${stock_price:.2f} each for ${cost:.2f}. Remaining balance: ${remaining_balance:.2f}"
    except Exception as e:
        return False, f"Failed to buy {ticker}: {str(e)}"

