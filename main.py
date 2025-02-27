import discord
import os
import asyncio
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import pandas as pd
import random
import time
from typing import Optional, List, Tuple
from stockpick import get_random_stock_info

load_dotenv("secret.env")
#placeholders
#replace these with stock market api implementation

option1 = 'option1'
option2 = 'option2'

#poll duration; 1 hour
duration = 30

log = ('log.csv')

token = os.getenv("DISCORD_TOKEN")
#intializing
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

#ready command
@bot.event
async def on_ready():
    print('Bot updated and ready for use')
    print('-----------------------------')


@bot.tree.command(name="bottest", description="Tests if the bot is functional")
async def bottest(interaction: discord.Interaction):
    await interaction.response.send_message("bot functional: tests passed")
    print('Test complete')

@bot.tree.command(name="poll", description="Start a poll")
async def poll(interaction: discord.Interaction):
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
    
    await interaction.response.send_message(embed=embed)
    
    poll_message = await interaction.original_response()
    await poll_message.add_reaction(emoji1)
    await poll_message.add_reaction(emoji2)
    
    bot.loop.create_task(count_votes(interaction, poll_message.id, option1, option2))

async def count_votes(interaction: discord.Interaction, message_id, option1, option2):
    await asyncio.sleep(duration)
    channel = interaction.channel
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
    
    await channel.send(f"Stock pick winner:\n{winner}")

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    if not os.path.isfile(log):
        df = pd.DataFrame(columns=['Timestamp', 'Winner'])
        df.to_csv(log, index=False)
    
    new_data = pd.DataFrame({
        'Timestamp': [timestamp],
        'Winner': [winner]
    })
    new_data.to_csv(log, mode='a', header=False, index=False)


bot.run(token)