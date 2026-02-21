import os, sys
import json
from typing import List

from snowflake_util import *
from web_well_information import search_well

def json_to_list(j) -> List:
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
    row[12]: VOLUME_UNITS
    row[13]: TYPE_TREATMENT
    row[14]: ACID_PCT
    row[15]: LBS_PROPPANT
    row[16]: MAX_TREATMENT_PRESSURE_PSI
    row[17]: MAX_TREATMENT_RATE_BBLS_MIN
    row[18]: DETAILS
    """
    output = [
        j["well_info"]["well_name_and_number"],
        j["well_info"]["api"],
        j["well_info"]["county_state"],
        j["well_info"]["well_shl"],
        j["well_info"]["datum"],
        j["stimulation_data"]["date_stimulated"],
        j["stimulation_data"]["stimulated_formation"],
        j["stimulation_data"]["top_ft"],
        j["stimulation_data"]["bottom_ft"],
        j["stimulation_data"]["stimulated_in"],
        j["stimulation_data"]["stimulation_stages"],
        j["stimulation_data"]["volume"],
        j["stimulation_data"]["volume_units"],
        j["stimulation_data"]["type_treatment"],
        j["stimulation_data"]["acid_pct"],
        j["stimulation_data"]["lbs_proppant"],
        j["stimulation_data"]["max_treatment_pressure_psi"],
        j["stimulation_data"]["max_treatment_rate_bbls_min"],
        j["stimulation_data"]["details"]
    ]

    for i in range(len(output)):
        output[i] = str(output[i])

    return output

if __name__ == "__main__":
    conn = get_connector()
    
    with open("well_information_from_pdf.json") as fp:
        j = json.load(fp)

    before_data = list(map(json_to_list, j))

    for i, data in enumerate(before_data):
        if i % 3 == 0:
            print(f"\rUpload BEFORE table [{i}/{len(before_data)}]...",
                  end="")
        set_before(conn, data)

    print("\rComplete Upload BEFORE table")
    
    before_df = get_before(conn)

    middle_data = [(before_df.iloc[i, 0], before_df.iloc[i, 1])\
                   for i in range(len(before_df))]
    
    after_data = []
    for i, data in enumerate(middle_data):
        if i % 3 == 0:
            print(f"\rRetrieve Extra Info [{i}/{len(middle_data)}]...",
                  end="")
        after_data.append(search_well(data[0], data[1]))

    print("\rComplete retrieve Extra Info")

    for i, data in enumerate(after_data):
        if i % 3 == 0:
            print(f"\rUpload AFTER table [{i}/{len(after_data)}]...",
                  end="")
        set_after(conn, data)

    print("\rComplete Upload AFTER table")

    after_df = get_after(conn)
