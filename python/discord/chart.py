import os
import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import discord
from discord.ext import commands
from discord import Intents

## Load database credentials and Discord token from environment variables
host = os.environ['HOST']
port = os.environ['PORT']
database = os.environ['DATABASE']
user = os.environ['USER']
password = os.environ['PASSWORD']
discord_token = os.environ['DISCORD_TOKEN']

## Set up Discord bot with intents for messages and message content
intents = Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def create_db_engine():
    """Create an engine that connects to the PostgreSQL server."""
    return create_engine(f'postgresql+psycopg2://{user}:{password}@{host}/{database}')

def get_data_from_db():
    """Get the launches by faction and timestamp for the current month from the qonqr.atlantis_launches table."""
    query = f"""
    SELECT 
            FACTION
        ,   TIMESTAMP
        ,   LAUNCHES 
    FROM
            qonqr.atlantis_launches 
    WHERE   DATE_TRUNC('month',timestamp)
        =   DATE_TRUNC('month',CURRENT_DATE)
    """

    ## Create a database engine and execute the query, returning a pandas dataframe
    engine = create_db_engine()
    with engine.begin() as conn:
        return pd.read_sql_query(query, conn)

def process_data(data):
    ## Process the data to prepare it for plotting.
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    ## Group the data by faction and timestamp, then sum the launches within each group.
    grouped_data = data.groupby(['faction','timestamp'])['launches'].sum().reset_index()

    ## Pivot the data so that each faction has its own column
    return grouped_data.pivot(index='timestamp', columns='faction', values='launches')

def plot_data(data):
    ## Create a line chart with different colors for each faction
    chart = data.plot(color=['purple','red','green'])

    ## Set the title, labels and legend of the chart
    chart.set_title('Atlantis Launches Over Time')
    chart.set_xlabel('Time')
    chart.set_ylabel('Launch Count')
    chart.legend(title='Faction')
    xmin, xmax = data.index.min(), data.index.max()
    chart.set_xlim(xmin, xmax)

    ## Format the x-axis ticks as dates
    chart.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%b-%d'))

    ## Save the chart as an image file
    image = chart.get_figure()
    with open('export.png', 'wb') as f:
        image.savefig(f)


@bot.command(name='chart')
async def chart(ctx):
    """Define a command that runs a Python script to plot the data from the database and send it to Discord."""
    ## Get the data from the database
    data = get_data_from_db()
    ## Process the data for plotting
    processed_data = process_data(data)
    ## Plot the data and save it as an image file
    plot_data(processed_data)
    ## Send the image file to Discord
    with open('export.png', 'rb') as f:
        await ctx.send(file=discord.File(f, 'export.png'))
    ## Clear command
    await ctx.message.delete()

bot.run(discord_token)
