import discord
import os
import asyncio
from discord.ext import commands
from discord import app_commands
import pandas as pd
import random
import time
from typing import Optional, List, Tuple

#placeholders
#replace these with stock market api implementation

option1 = 'option1'
option2 = 'option2'

#poll duration; 1 hour
duration = 3600

log = ('log.csv')

token = ''

#intializing
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

#ready command
@bot.event
async def on_ready():
    print('Bot updated and ready for use')
    print('-----------------------------')


@bot.command()
async def bottest(ctx):
    await ctx.send('bot functional: tests passed')
    print('Test complete')

@bot.command()
async def poll(ctx):
    emoji1 = '1️⃣'
    emoji2 = '2️⃣'
    #creating poll embed
    embed = discord.Embed(
        title="Poll", 
        description=f"{emoji1} {option1}\n{emoji2} {option2}",
        color = discord.Color.blue()
    )
    poll_message = await ctx.send(embed=embed)
    await(poll_message.add_reaction(emoji1))
    await(poll_message.add_reaction(emoji2))

    bot.loop.create_task(count_votes(ctx, poll_message.id))

async def count_votes(ctx, message_id):
    await asyncio.sleep(duration)
    channel = ctx.channel
    message = await channel.fetch_message(message_id)
    count1 = 0
    count2 = 0

    #ignore bot's own reactions
    for reaction in message.reactions:
        if str(reaction.emoji) == '1️⃣':
            count1 = reaction.count - 1
        elif str(reaction.emoji) == '2️⃣':
            count2 = reaction.count - 1
        
    await ctx.send(f"Poll ended, results:\n{option1}: {count1}\n{option2}: {count2}")


#replace with token
bot.run(token)