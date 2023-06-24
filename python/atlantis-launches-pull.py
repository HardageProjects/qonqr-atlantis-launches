# Import libraries
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timezone
import urllib3
import psycopg2
from sqlalchemy import create_engine, text
import sys
import os

# Disable warnings to ensure code runs (probably not the safest idea)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Grab timestamp
timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

# Make request to go to URL
url = requests.get('https://portal.qonqr.com/Atlantis',verify=False)

# Parse HTML content using bs4
parse = BeautifulSoup(url.text, 'html.parser')

#Check if battle is on-going, and stop the script if it is over
battle_status = []
for div_tag in parse.find_all('div',{'class':'col-md-12 col-xs-12'}):
    # Find text within <h1> tag
    h1_tag = div_tag.find('h1')
    text_in_h1 = h1_tag.get_text(strip=True)

# check = text_in_h1.find("under way")
# if check < 0:
#     print('No on-going battle at ' + timestamp)
#     sys.exit()
    
#Extract information
bottom_launchers = []
for tr_tag in parse.find_all('tr', {'class':['Swarm','Legion','Faceless']}):
    td_tags = tr_tag.find_all('td')
    row = []
    for td_tag in td_tags:
        text = td_tag.get_text()
        components = text.split()
        new_components = []
        i = 0
        while i < len(components):
            if i < len(components) - 1 and components[i].isdigit() and components[i+1].isdigit():
                new_components.append(''.join(components[i:i+2]))
                i += 2
            else:
                new_components.append(components[i])
                i += 1
        row.extend(new_components)
    faction = tr_tag.get('class')[0]
    row.append(faction)
    bottom_launchers.append(row)

bottom_launches = [[x.replace(" ","") for x in row] + [timestamp] for row in bottom_launchers]

bottom_df = pd.DataFrame(bottom_launches, columns=['Rank','player','launches','faction','timestamp'])

bottom_df = bottom_df.drop('Rank',axis=1)

top_launchers = []
for div_tag in parse.find_all('div',{'class':'col-xs-7'}):
    # Find text within <a> tag
    h3_tag = div_tag.find('h3')
    a_tag = h3_tag.find('a')
    text_in_a = a_tag.get_text(strip=True)
    
    #Find text within third <h5> tag
    h5_tags = div_tag.find_all('h5')
    if len(h5_tags) >= 3:
        text_in_h5 = h5_tags[2].get_text(strip=True)
    else:
        text_in_h5 = ''
        
    top_launchers.append((text_in_a,text_in_h5.replace(" ","")))
    
top_df = pd.DataFrame(top_launchers, columns=['player','launches'])

filtered_data = []

for index, row in top_df.iterrows():
    if row['launches'] != '':
        filtered_data.append(row)
    
filtered_df = pd.DataFrame(filtered_data)
filtered_df['faction'] = ''
filtered_df['timestamp'] = timestamp

for index, row in filtered_df.iterrows():
    if index >= 1 and index <= 3:
        filtered_df.at[index, 'faction'] = 'Swarm'
    elif index >= 4 and index <= 6:
        filtered_df.at[index, 'faction'] = 'Legion'
    elif index >= 7 and index <= 9:
        filtered_df.at[index, 'faction'] = 'Faceless'

combined_df = pd.concat([bottom_df, filtered_df],ignore_index=True)
combined_df['launches'] = pd.to_numeric(combined_df['launches'])

# Sort combined_df by 'Launches' in descending order and then by 'Faction'
sorted_df = combined_df.sort_values(by=['faction','launches'], ascending=[True,False])

host = os.environ['HOST']
port = os.environ['PORT']
database = os.environ['DATABASE']
user = os.environ['USER']
password = os.environ['PASSWORD']

# Create an engine that connects to the PostgreSQL server
engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}/{database}')

# Define a SQL query to find the maximum existing ID value
query = 'SELECT MAX(id) FROM qonqr.atlantis_launches'

# Fetch results
with engine.begin() as conn:
    result = pd.read_sql_query(query, conn)

max_id = result.iloc[0][0]

# Generate new unique IDs for each row of the new data
new_ids = range(max_id + 1, max_id + len(sorted_df) + 1)

# Assign the new IDs to the ID column of the new data
sorted_df['id'] = new_ids

# Write the DataFrame to a table in the PostgreSQL database
sorted_df.to_sql('atlantis_launches', engine, if_exists='append', index=False,schema='qonqr')
