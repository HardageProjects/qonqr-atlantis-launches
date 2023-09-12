import os
import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
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

color_dict = {'Faceless':'purple','Legion':'red','Swarm':'green'}

def create_db_engine():
    """Create an engine that connects to the PostgreSQL server."""
    return create_engine(f'postgresql+psycopg2://{user}:{password}@{host}/{database}')

def get_faction_data_from_db():
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

def get_player_data_from_db():
    """Get the launches by player, faction, and timestamp for the current month from the qonqr.atlantis_launches table."""
    query = f"""
    SELECT 
            FACTION
        ,   PLAYER
        ,   TIMESTAMP
        ,   LAUNCHES 
    FROM
            qonqr.atlantis_launches 
    WHERE   timestamp IN (SELECT MAX(TIMESTAMP) FROM qonqr.atlantis_launches)
    """

    ## Create a database engine and execute the query, returning a pandas dataframe
    engine = create_db_engine()
    with engine.begin() as conn:
        return pd.read_sql_query(query, conn)

def process_faction_data(data):
    ## Process the data to prepare it for plotting faction data.
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    ## Group the data by faction and timestamp, then sum the launches within each group.
    grouped_data = data.groupby(['faction','timestamp'])['launches'].sum().reset_index()

    ## Pivot the data so that each faction has its own column
    return grouped_data.pivot(index='timestamp', columns='faction', values='launches')

def process_rank_data(data):
    ## Process the data to prepare it for plotting rank data.
    #data.drop('timestamp', axis=1, inplace=True)

    ## Rank players in each faction by their launches
    data['rank'] = data.groupby('faction')['launches'].rank(ascending=False)

    return data

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
    ## Set the y-axis minimum to zero
    chart.set_ylim([0,None])

    ## Add grid lines to horizontal tick marks
    chart.yaxis.grid(True, linestyle='-',linewidth=0.5)

    ## Format the x-axis ticks as dates
    chart.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%b-%d'))

    ## Add vertical lines at the start of each day and at the start of the dataset
    start_date = data.index.min().date()
    end_date = data.index.max().date()
    for date in pd.date_range(start_date, end_date):
            chart.axvline(x=date, color='black', linestyle='-', linewidth=0.25)

    ## Format x-axis ticks as dates and align the labels to the left (which should center the label)
    chart.xaxis.set_major_locator(mdates.DayLocator())
    chart.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%b-%d'))
    for label in chart.get_xticklabels():
        label.set_horizontalalignment('left')

    ## Save the chart as an image file
    image = chart.get_figure()
    with open('export_line.png', 'wb') as f:
        image.savefig(f)

    ## Clear the figure
    plt.clf()

def plot_proportional_data(data):
    ## Create a stacked percentage chart with different colors for each faction
    data = data.apply(lambda x: x/x.sum(), axis=1)
    chart = data.plot(kind='area', stacked=True, color=['purple','red','green'])

    ## Set the title, labels, and legend of the chart
    chart.set_title('Proportional Atlantis Launches Over Time')
    chart.set_xlabel('Date')
    chart.set_ylabel('Launch Proportion')
    chart.legend(title='Faction').set_visible(False)
    xmin, xmax = data.index.min(), data.index.max()
    chart.set_xlim(xmin, xmax)
    ## Set the y-axis limits to the exact range of the data
    ymin, ymax = 0, 1
    chart.set_ylim(ymin, ymax)


    ## Add horizontal lines at y=0.33 and y=0.67
    chart.axhline(y=0.33, color='gray', linestyle='--', linewidth=1)
    chart.axhline(y=0.67, color='gray', linestyle='--', linewidth=1)

    ## Add vertical lines at the start of each day and at the start of the dataset
    start_date = data.index.min().date()
    end_date = data.index.max().date()
    for date in pd.date_range(start_date, end_date):
            chart.axvline(x=date, color='black', linestyle='-', linewidth=0.25)

    ## Add labels to display the proportion of each faction at the end of each day
    for date in data.index:
        if date == data[data.index.date == date.date()].index[-1] or date == data.index[-1]:
            y = 0
            for faction in data.columns:
                proportion = data.loc[date, faction]
                chart.annotate(f'{proportion:.0%}', xy=(date, y + proportion/2), xytext=(0, 0), textcoords='offset points', ha='right', va='top', fontsize=10, bbox=dict(facecolor='white',edgecolor='none',alpha=0.5))
                y += proportion

    ## Format x-axis ticks as dates and align the labels to the left (which should center the label)
    chart.xaxis.set_major_locator(mdates.DayLocator())
    chart.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%b-%d'))
    for label in chart.get_xticklabels():
        label.set_horizontalalignment('left')

    ## Save the chart as an image file
    image = chart.get_figure()
    with open('proportional_export.png', 'wb') as f:
        image.savefig(f)

    ## Clear the figure
    plt.clf()

def plot_box(data, log_scale):
    ## Create a box-and-whisker plot with different colors for each faction
    chart = sns.boxplot(data=data, x='faction', y='launches', palette=color_dict)

    ## Set the title, labels and legend of the chart
    chart.set_title('Distribution of Player Launches Within Each Faction')
    chart.set_xlabel('Faction')
    chart.set_ylabel('Launch Count')
    if log_scale:
        plt.yscale('log')

    ## Save the chart as an image file
    image = chart.get_figure()
    with open('export_box.png', 'wb') as f:
        image.savefig(f)

    ## Clear the figure
    plt.clf()

def plot_violin(data): 
    ## Create a violin plot with different colors for each faction
    chart = sns.violinplot(data=data, x='faction', y='launches', palette=color_dict, inner="point", cut = 0)

    ## Set the title, labels, and legend of the chart
    chart.set_title('Violin Plot of Player Launches Within Each Faction')
    chart.set_xlabel('Faction')
    chart.set_ylabel('Launch Count')

    ## Save the chart as an image file
    image = chart.get_figure()
    with open('export_violin.png', 'wb') as f:
        image.savefig(f)

    ## Clear the figure
    plt.clf()

def plot_rank(data, log_scale):
    ## Create a strip plot with different colors for each faction
    chart = sns.stripplot(x='rank', y='launches', hue='faction', data=data, palette=color_dict)

    plt.title('Player Ranks by Faction')
    plt.xlabel('Rank')
    plt.ylabel('Launches')
    chart.legend(title='Faction')
    plt.xticks(ticks=range(0, int(data['rank'].max()), 10), labels=range(0,int(data['rank'].max()), 10))
    if log_scale:
        plt.yscale('log')

    ## Save the chart as an image file
    image = chart.get_figure()
    with open('rank_chart.png', 'wb') as f:
        image.savefig(f)

    ## Clear the figure
    plt.clf()

@bot.command(name='chart')
async def chart(ctx):
    """Define a command that runs a Python script to plot the data from the database and send it to Discord."""
    ## Get the data from the database
    data = get_faction_data_from_db()
    ## Process the data for plotting
    processed_data = process_faction_data(data)
    ## Plot the data and save it as an image file
    plot_data(processed_data)
    ## Send the image file to Discord
    with open('export_line.png', 'rb') as f:
        await ctx.send(file=discord.File(f, 'export_line.png'))
    ## Clear command
    await ctx.message.delete()

@bot.command(name='chart%')
async def proportional_chart(ctx):
    """Define a command that runs a Python script to plot the proportional data from the database and send it to Discord."""
    ## Get the data from the database
    data = get_faction_data_from_db()
    ## Process the data for plotting
    processed_data = process_faction_data(data)
    ## Plot the data and save it as an image file
    plot_proportional_data(processed_data)
    ## Send the image file to Discord
    with open('proportional_export.png', 'rb') as f:
        await ctx.send(file=discord.File(f, 'proportional_export.png'))
    ## Clear command
    await ctx.message.delete()

@bot.command(name='box')
async def box(ctx):
    """Define a command that runs a Python script to create a box-and-whisker chart from the database and send it to Discord."""
    ## Get the player data from the database
    player_data = get_player_data_from_db()
    ## Plot a box-and-whisker plot and save it as an image file
    plot_box(player_data, log_scale=False)
    ## Send the image file to Discord
    with open('export_box.png', 'rb') as f:
        await ctx.send(file=discord.File(f, 'export_box.png'))
    ## Clear command
    await ctx.message.delete()

@bot.command(name='boxlog')
async def boxlog(ctx):
    """Define a command that runs a Python script to create a box-and-whisker chart from the database and send it to Discord."""
    ## Get the player data from the database
    player_data = get_player_data_from_db()
    ## Plot a box-and-whisker plot and save it as an image file
    plot_box(player_data, log_scale=True)
    ## Send the image file to Discord
    with open('export_box.png', 'rb') as f:
        await ctx.send(file=discord.File(f, 'export_box.png'))
    ## Clear command
    await ctx.message.delete()

@bot.command(name='violin')
async def violin_plot(ctx):
    """Define a command that runs a Python script to create a violin plot from the database and send it to Discord."""
    ## Get the player data from the database
    player_data = get_player_data_from_db()
    ## Plot a violin plot and save it as an image file
    plot_violin(player_data)
    ## Send the image file to Discord
    with open('export_violin.png', 'rb') as f:
        await ctx.send(file=discord.File(f, 'export_violin.png'))
    ## Clear command
    await ctx.message.delete()

@bot.command(name='rank')
async def rank_plot(ctx):
    """Define a command that runs a Python script to create a strip plot from the database and send it to Discord."""
    ## Get player data from the database
    player_data = get_player_data_from_db()
    ## Process the data for plotting
    processed_data = process_rank_data(player_data)
    ## Plot a strip plot and save it as an image file
    plot_rank(processed_data, log_scale=False)
    ## Send the image file to Discord
    with open('rank_chart.png', 'rb') as f:
        await ctx.send(file=discord.File(f, 'rank_chart.png'))
    ## Clear command
    await ctx.message.delete()

@bot.command(name='ranklog')
async def rank_plot(ctx):
    """Define a command that runs a Python script to create a strip plot from the database and send it to Discord."""
    ## Get player data from the database
    player_data = get_player_data_from_db()
    ## Process the data for plotting
    processed_data = process_rank_data(player_data)
    ## Plot a strip plot and save it as an image file
    plot_rank(processed_data, log_scale=True)
    ## Send the image file to Discord
    with open('rank_chart.png', 'rb') as f:
        await ctx.send(file=discord.File(f, 'rank_chart.png'))
    ## Clear command
    await ctx.message.delete()

bot.run(discord_token)