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
        cur.execute("SELECT WELL_NAME, API_NO FROM PUBLIC.BEFORE")
        df = cur.fetch_pandas_all()
    return df

def set_before(conn, row: List):
    """
    row[0]: WELL_NAME
    row[1]: API_NO
    row[2]: COUNTY_STATE
    row[3]: well_shl
    row[4]: DATUM
    row[5]: DATE_STIMULATED
    row[6]: STIMULATED_FORMATION
    row[7]: TOP_FT
    row[8]: BOTTOM_FT
    row[9]: STIMULATED_IN
    row[10]: STIMUALTED_STAGES
    row[11]: VOLUME_
    row[12]: VOLUME_UNITS,
    row[13]: TYPE_TREATMENT
    row[14]: ACID_PCT
    row[15]: LBS_PROPPANT
    row[16]: MAX_TREATMENT_PRESSURE_PSI
    row[17]: MAX_TREATMENT_RATE_BBLS_MIN
    row[18]: DETAILS
    """
    if not (row[0] or row[1]):
        return
    
    values = ""
    for i in range(len(row)):
        if row[i]:
            row[i] = row[i].replace("'", '')
            values += f"'{row[i]}',"
        else:
            values += "NULL,"

    values = values[:-1]
    
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO PUBLIC.BEFORE VALUES ({values})
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
    if not (row[0] or row[1]):
        return
    
    values = ""
    for i in range(len(row)):
        if row[i]:
            row[i] = row[i].replace("'", '')
            values += f"'{row[i]}',"
        else:
            values += "NULL,"

    values = values[:-1]
            
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO PUBLIC.AFTER VALUES ({values})
            """)

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
    
