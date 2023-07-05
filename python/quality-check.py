import psycopg2
from sqlalchemy import create_engine
import pandas as pd

host = os.environ['HOST']
port = os.environ['PORT']
database = os.environ['DATABASE']
user = os.environ['USER']
password = os.environ['PASSWORD']

# Create an engine that connects to the PostgreSQL server
engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}/{database}')

query = """
SELECT
                COUNT(ID)   AS ROW_COUNT
        ,       DATE_TRUNC('second',NOW() AT TIME ZONE 'America/Chicago' - (MAX(TIMESTAMP AT TIME ZONE 'UTC')) AT TIME ZONE 'America/Chicago') AS TIME_SINCE_UPDATE
FROM
        qonqr.atlantis_launches
"""

with engine.begin() as conn:
    result = pd.read_sql_query(query, conn)

row_count = result.iloc[0][0]
time_since_update = result.iloc[0][1]

print(f"It has been {time_since_update} since the last update. The table has {row_count} rows.")