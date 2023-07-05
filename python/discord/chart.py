import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import discord
from discord.ext import commands
from discord import Intents
import os

host = os.environ['HOST']
port = os.environ['PORT']
database = os.environ['DATABASE']
user = os.environ['USER']
password = os.environ['PASSWORD']
discord_token = os.environ['DISCORD_TOKEN']
channel_id = 556885461210103822

## Set up Discord bot
intents = Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

## Define a command that runs a Python script
@bot.command(name='chart')

async def chart(ctx):
    if ctx.channel.id == channel_id:
        await ctx.message.delete()

        # Create an engine that connects to the PostgreSQL server
        engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}/{database}')

        # Define a SQL query to find the maximum existing ID value
        query = 'SELECT FACTION, TIMESTAMP, LAUNCHES FROM qonqr.atlantis_launches WHERE DATE_TRUNC(\'month\',TIMESTAMP) = DATE_TRUNC(\'month\',CURRENT_DATE)'
        # 'SELECT * FROM qonqr.atlantis_launches'
        with engine.begin() as conn:
            result = pd.read_sql_query(query, conn)

        # Convert timestamp to datetime
        result['timestamp'] = pd.to_datetime(result['timestamp'])

        # Group the data by faction and timestamp, then sum the launches within each group
        grouped_data = result.groupby(['faction','timestamp'])['launches'].sum().reset_index()

        # Pivot the data so that each faction has its own column
        pivoted_data = grouped_data.pivot(index='timestamp', columns='faction', values='launches')

        chart = pivoted_data.plot(color=['purple','red','green'])
        chart.set_title('Atlantis Launches Over Time')
        chart.set_xlabel('Time')
        chart.set_ylabel('Launch Count')
        chart.legend(title='Faction')
        chart.xaxis.set_major_formatter(mdates.DateFormatter('%B %d, %y %H:%M'))

        image = chart.get_figure()
        image.savefig('export.png')

        ##plt.show()
        with open('export.png', 'rb') as f:
            await ctx.send(file=discord.File(f, 'export.png'))

bot.run(discord_token)
