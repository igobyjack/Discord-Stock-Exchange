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
    """Initialize the balance file if it doesn't exist or is empty"""
    if not os.path.isfile(balance_file) or os.path.getsize(balance_file) == 0:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        df = pd.DataFrame({
            'Timestamp': [timestamp],
            'Balance': [INITIAL_BALANCE],
            'Action': ['Initial deposit'],
            'Amount': [INITIAL_BALANCE]
        })
        df.to_csv(balance_file, index=False)
        return INITIAL_BALANCE
    # If file exists and is non-empty, return the current balance.
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

def sell_stock(ticker, amount=None, shares=None):
    """Sell stock from portfolio and update cash balance
    
    Args:
        ticker (str): Stock ticker symbol
        amount (float, optional): Dollar amount to sell
        shares (int, optional): Number of shares to sell
        
    Returns:
        tuple: (success, message)
    """
    try:
        ticker_symbol = ticker.split()[0]
        
        # Check if we have this stock in portfolio
        if not os.path.isfile(portfolio_file):
            return False, f"No portfolio exists to sell {ticker_symbol} from"
        
        df = pd.read_csv(portfolio_file)
        if df.empty:
            return False, f"Empty portfolio, no {ticker_symbol} shares to sell"
        
        # Get total shares owned
        portfolio_stock = df[df['Ticker'] == ticker_symbol]
        if portfolio_stock.empty:
            return False, f"You don't own any shares of {ticker_symbol}"
            
        total_shares_owned = portfolio_stock['Shares'].sum()
        
        # Get current market price
        stock = yf.Ticker(ticker_symbol)
        stock_price = stock.history(period='1d')['Close'][0]
        stock_info = stock.info
        company_name = stock_info.get('longName', ticker_symbol)
        
        # Determine shares to sell and sale value
        if shares is not None:
            shares_to_sell = shares
            if shares_to_sell > total_shares_owned:
                return False, f"You only have {total_shares_owned} shares of {company_name}, cannot sell {shares_to_sell}"
            sale_value = shares_to_sell * stock_price
        else:
            # If amount specified, convert to shares (limited by owned shares)
            max_sale_value = total_shares_owned * stock_price
            if amount > max_sale_value:
                shares_to_sell = total_shares_owned
                sale_value = max_sale_value
            else:
                shares_to_sell = amount // stock_price
                sale_value = shares_to_sell * stock_price
        
        # Update portfolio: reduce shares owned
        # We'll subtract from the most recent purchases first (LIFO)
        # Create a new DataFrame without the sold shares
        shares_left_to_sell = shares_to_sell
        new_portfolio = []
        
        # Process in reverse order (most recent first)
        for idx, row in df.iloc[::-1].iterrows():
            if row['Ticker'] == ticker_symbol and shares_left_to_sell > 0:
                # This row contains shares we want to sell
                if row['Shares'] <= shares_left_to_sell:
                    # Sell all shares in this row
                    shares_left_to_sell -= row['Shares']
                else:
                    # Sell only part of the shares in this row
                    new_shares = row['Shares'] - shares_left_to_sell
                    row_copy = row.copy()
                    row_copy['Shares'] = new_shares
                    new_portfolio.append(row_copy)
                    shares_left_to_sell = 0
            else:
                # Keep this row unchanged
                new_portfolio.append(row)
        
        # Convert back to DataFrame and save
        if new_portfolio:
            new_df = pd.DataFrame(new_portfolio)
            # Sort by original order (earliest first)
            new_df = new_df.iloc[::-1]
            new_df.to_csv(portfolio_file, index=False)
        else:
            # Portfolio is now empty, create empty file with headers
            pd.DataFrame(columns=['Timestamp', 'Ticker', 'Name', 'Shares', 'Price', 'Total']).to_csv(portfolio_file, index=False)
        
        # Update cash balance (negative amount means adding money)
        update_balance(-sale_value, f"Sell {ticker_symbol}")
        
        # Get the updated balance
        new_balance = get_balance()
        
        return True, f"Sold {shares_to_sell} shares of {company_name} ({ticker_symbol}) at ${stock_price:.2f} each for ${sale_value:.2f}. New balance: ${new_balance:.2f}"
            
    except Exception as e:
        return False, f"Failed to sell {ticker}: {str(e)}"