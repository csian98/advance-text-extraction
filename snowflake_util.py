import os, sys
from typing import List
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

load_dotenv("./.env")

def get_connector():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
    )

def get_before(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM PUBLIC.BEFORE")
        df = cur.fetch_pandas_all()
    return df

def set_before(conn, row: List):
    """
    row[0]: WELL_NAME
    row[1]: API_NO
    """
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO PUBLIC.BEFORE VALUES ('{row[0]}', '{row[1]}')
            """)

def get_after(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM PUBLIC.AFTER")
        df = cur.fetch_pandas_all()
    return df

def set_after(conn, row: List):
    """
    row[0]: Well Name
    row[1]: API No
    row[2]: Operator
    row[3]: Well Status
    row[4]: Well Type
    row[5]: Closest City
    row[6]: Latitude
    row[7]: Longitude
    row[8]: Oil produced | Optional[str]
    row[9]: Gas produced | Optional[str]
    """
    def check(row: List) -> bool:
        for i in range(8):
            if not row[i]:
                return False
        
        return True
    
    if not check(row):
        return
    
    for i in range(8, 10):
        if row[i]:
            row[i] = "'" + row[i] + "'"
            
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO PUBLIC.AFTER VALUES (
            	'{row[0]}', '{row[1]}', '{row[2]}',
            	'{row[3]}', '{row[4]}', '{row[5]}',
            	'{row[6]}', '{row[7]}',
            	{row[8] if row[8] else 'NULL'},
            	{row[9] if row[9] else 'NULL'}
            )""")

from web_well_information import search_well
if __name__ == "__main__":
    conn = get_connector()
    well_name = "Kline Federal 5300 31-18 7T"
    api = "33-053-06056"

    set_before(conn, [well_name, api])
    before_df = get_before(conn)
    print(before_df)

    row = search_well(before_df.iloc[0, 0], before_df.iloc[0, 1])
    set_after(conn, row)
    after_df = get_after(conn)
    print(after_df)
    
