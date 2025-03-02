import discord
import os
import asyncio
import datetime
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import pandas as pd
import random
import time
from typing import Optional, List, Tuple
from stockpick import get_random_stock_info
import yfinance as yf
from portfolio import buy_stock, sell_stock

load_dotenv("token.env")

# poll duration; 1 hour
duration = 30

token = os.getenv("DISCORD_TOKEN")

# Channel ID where auto polls should be posted
AUTO_POLL_CHANNEL_ID = 1344497262444941355  # Replace with your actual channel ID

#intializing
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

#ready command
@bot.event
async def on_ready():
    from portfolio import initialize_balance
    print('Bot updated and ready for use')
    initialize_balance()  # Initialize the balance
    
    # Sync all slash commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    # Start the auto poll scheduler
    auto_poll_scheduler.start()
    
    print('-----------------------------')

# Function to create a poll that works without interaction
async def create_poll(channel):
    emoji1 = '1️⃣'
    emoji2 = '2️⃣'
    
    # Get two different random stocks
    stock1 = get_random_stock_info()
    stock2 = get_random_stock_info()
    
    # Make sure we get two different stocks
    while stock2['Name'] == stock1['Name']:
        stock2 = get_random_stock_info()
    
    option1 = stock1['Name']
    option2 = stock2['Name']
    
    embed = discord.Embed(
        title="Next stock pick", 
        description=f"{emoji1}  {option1}\n\n{emoji2}  {option2}",
        color=discord.Color.blue()
    )
    
    poll_message = await channel.send(embed=embed)
    await poll_message.add_reaction(emoji1)
    await poll_message.add_reaction(emoji2)
    
    # Schedule vote counting
    bot.loop.create_task(count_votes_auto(channel, poll_message.id, option1, option2))

# Counting votes for auto polls
async def count_votes_auto(channel, message_id, option1, option2):
    await asyncio.sleep(duration)
    message = await channel.fetch_message(message_id)
    count1 = 0
    count2 = 0
    # ignore bot's own reactions
    for reaction in message.reactions:
        if str(reaction.emoji) == '1️⃣':
            count1 = reaction.count - 1
        elif str(reaction.emoji) == '2️⃣':
            count2 = reaction.count - 1
    
    if count1 > count2:
        winner = option1
    elif count2 > count1:
        winner = option2
    else:
        winner = 'Tie'
    

    if winner != 'Tie':
        await channel.send(f"Stock pick winner:\n{winner}")
        success, message_text = buy_stock(winner, shares=1)
        await channel.send(f"{message_text}")
    else:
        await channel.send("Tie, no stock picked")

@tasks.loop(minutes=1.0)
async def auto_poll_scheduler():
    now = datetime.datetime.now()
    
    # Check if it's 9 PM (21:00)
    if now.hour == 21 and now.minute == 0:
        print("Triggering automatic poll")
        channel = bot.get_channel(AUTO_POLL_CHANNEL_ID)
        if channel:
            await create_poll(channel)
        else:
            print(f"Error: Could not find channel with ID {AUTO_POLL_CHANNEL_ID}")

# Wait until bot is ready before starting scheduler
@auto_poll_scheduler.before_loop
async def before_auto_poll():
    await bot.wait_until_ready()

# Original commands remain unchanged
@bot.tree.command(name="bottest", description="Tests if the bot is functional")
async def bottest(interaction: discord.Interaction):
    await interaction.response.send_message("bot functional: tests passed")
    print('Test complete')


@bot.tree.command(name="portfolio", description="View current portfolio status")
async def portfolio_cmd(interaction: discord.Interaction):
    from portfolio import get_portfolio_value, initialize_balance
    
    # Initialize balance if needed
    initialize_balance()
    
    # Get portfolio data
    portfolio_data = get_portfolio_value()
    
    embed = discord.Embed(
        title="Portfolio Status",
        description="Current portfolio value and holdings",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Cash Balance", value=f"${portfolio_data['cash']:.2f}", inline=False)
    embed.add_field(name="Stock Value", value=f"${portfolio_data['stocks']:.2f}", inline=False)
    embed.add_field(name="Total Value", value=f"${portfolio_data['total']:.2f}", inline=False)
    
    # Add individual stock holdings if portfolio.csv exists
    if os.path.exists('portfolio.csv'):
        df = pd.read_csv('portfolio.csv')
        if not df.empty:
            holdings = df.groupby('Ticker').agg({
                'Name': 'first',
                'Shares': 'sum'
            })
            
            stocks_text = ""
            for ticker, row in holdings.iterrows():
                try:
                    stock = yf.Ticker(ticker)
                    current_price = stock.history(period='1d')['Close'][0]
                    value = row['Shares'] * current_price
                    stocks_text += f"**{ticker}** ({row['Name']}): {row['Shares']} shares - ${value:.2f}\n"
                except:
                    stocks_text += f"**{ticker}** ({row['Name']}): {row['Shares']} shares\n"
            
            if stocks_text:
                embed.add_field(name="Holdings", value=stocks_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="value", description="Get the current portfolio value")
async def value_cmd(interaction: discord.Interaction):
    from portfolio import get_portfolio_value, initialize_balance
    
    # Initialize balance if needed
    initialize_balance()
    
    # Get portfolio data
    portfolio_data = get_portfolio_value()
    
    # Calculate the profit/loss
    profit_loss = portfolio_data['total'] - 50000  # 50000 is the initial balance
    profit_loss_percent = (profit_loss / 50000) * 100
    
    # Determine if it's profit or loss
    if profit_loss >= 0:
        status = f"📈 Profit: +${profit_loss:.2f} (+{profit_loss_percent:.2f}%)"
        color = discord.Color.green()
    else:
        status = f"📉 Loss: -${abs(profit_loss):.2f} ({profit_loss_percent:.2f}%)"
        color = discord.Color.red()
    
    # Create a simple embed
    embed = discord.Embed(
        title="Portfolio Value",
        description=f"**${portfolio_data['total']:.2f}**\n{status}",
        color=color
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sellpoll", description="Start a poll to decide which stock to sell")
async def sellpoll(interaction: discord.Interaction):
    
    # Check if we have stocks in portfolio
    if not os.path.exists('portfolio.csv'):
        await interaction.response.send_message("No stocks in portfolio to sell.")
        return
    
    df = pd.read_csv('portfolio.csv')
    if df.empty:
        await interaction.response.send_message("No stocks in portfolio to sell.")
        return
    
    # Group by ticker to get unique stocks
    holdings = df.groupby('Ticker').agg({
        'Name': 'first',
        'Shares': 'sum'
    })
    
    # Need at least 2 different stocks for a poll
    if len(holdings) < 2:
        await interaction.response.send_message(f"Need at least 2 different stocks for a poll. You only have {len(holdings)}.")
        return
    
    # Select 2 random stocks from portfolio
    selected_tickers = random.sample(list(holdings.index), 2)
    
    # Set up poll options
    emoji1 = '1️⃣'
    emoji2 = '2️⃣'
    
    option1 = f"{selected_tickers[0]} ({holdings.loc[selected_tickers[0]]['Name']})"
    option2 = f"{selected_tickers[1]} ({holdings.loc[selected_tickers[1]]['Name']})"
    
    embed = discord.Embed(
        title="Which stock should we sell?", 
        description=f"{emoji1}  {option1}\n\n{emoji2}  {option2}",
        color=discord.Color.red()
    )
    
    # Send the poll message
    poll_message = await interaction.channel.send(embed=embed)
    
    # Acknowledge the interaction
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Sell poll created!", ephemeral=True)
    
    # Add reactions for voting
    await poll_message.add_reaction(emoji1)
    await poll_message.add_reaction(emoji2)
    
    # Schedule vote counting
    bot.loop.create_task(count_sell_votes(interaction.channel, poll_message.id, selected_tickers[0], selected_tickers[1]))

# Count votes for sell polls
async def count_sell_votes(channel, message_id, option1, option2):
    await asyncio.sleep(duration)
    message = await channel.fetch_message(message_id)
    count1 = 0
    count2 = 0
    
    # Count votes (ignore bot's own reactions)
    for reaction in message.reactions:
        if str(reaction.emoji) == '1️⃣':
            count1 = reaction.count - 1
        elif str(reaction.emoji) == '2️⃣':
            count2 = reaction.count - 1
    
    # Determine winner
    if count1 > count2:
        winner = option1
    elif count2 > count1:
        winner = option2
    else:
        winner = 'Tie'
    
    if winner != 'Tie':
        await channel.send(f"Stock to sell:\n{winner}")
        success, message_text = sell_stock(winner, shares=1)
        await channel.send(f"{message_text}")
    else:
        await channel.send("Tie, no stock sold")

bot.run(token)