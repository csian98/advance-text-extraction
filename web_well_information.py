from typing import Optional, List
import requests
from bs4 import BeautifulSoup

def search_well(well_name: str, api: str) -> List:
    """
    https://www.drillingedge.com
    """
    def create_url(well_name: str, api: str) -> List:
        if not (well_name or api):
            return []
        
        urls = []
        endpoint = "https://www.drillingedge.com/search?type=wells"
        well_name = well_name.replace(' ', '+')
        
        if well_name and api:
            urls.append(endpoint + f"&well_name={well_name}&api_no={api}")
            
        # prioritize api
        if api:
            urls.append(endpoint + f"&well_name=&api_no={api}")
        if well_name:
            urls.append(endpoint + f"&well_name={well_name}&api_no=")
            
        return urls

    def get_hyperlink(url: str) -> str:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="table wide-table interest_table")
        row = table.select("tr[data-key]")
        
        # cannot specify
        if len(row) != 1:
            return None
        
        return row[0].find("a").attrs["href"]

    def get_extra_information(url: str) -> List:
        """
        0: Well Name
        1: API No
        2: Operator
        3: Well Status
        4: Well Type
        5: Closest City
        6: Latitude
        7: Longitude
        8: Oil produced | Optional[str]
        9: Gas produced | Optional[str]
        """
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="skinny")

        queries = ["Well Name", "API No.", "Operator",
                   "Well Status", "Well Type", "Closest City"]

        information = []
        for query in queries:
            th = table.find("th", string=query)
            if th:
                td = th.find_next_sibling("td")
                information.append(td.get_text(strip=True))
            else:
                information.append(None)

        query = "Latitude / Longitude"
        th = table.find("th", string=query)
        if th:
            td = th.find_next_sibling("td")
            latitude, longitude = td.get_text(strip=True).split(',')
            information.append(latitude.strip())
            information.append(longitude.strip())

        oil = None; gas = None
        p_tags = soup.find_all("p", class_="block_stat")
        for p_tag in p_tags:
            text = p_tag.get_text()
            if not oil and "oil" in text.lower():
                oil = p_tag.find("span").text
            elif not gas and "gas" in text.lower():
                gas = p_tag.find("span").text

        information.append(oil)
        information.append(gas)

        return information

    urls = create_url(well_name, api)
    hyperlink = ""
    
    for url in urls:
        link = get_hyperlink(url)
        if link:
            hyperlink = link
            break

    # cannot specify or no search result
    if not hyperlink:
        return [None] * 10

    return get_extra_information(hyperlink)

