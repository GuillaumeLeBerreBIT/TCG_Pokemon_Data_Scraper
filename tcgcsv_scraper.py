import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os 
import time
import csv
from requests_html import HTMLSession

class TCGCSVScraper:
    
    def __init__(self):
        
        self.url = 'https://tcgcsv.com/'
        self.headers= {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        
    def render_js(self):
        
        session = HTMLSession()
        r = session.get(self.url)
        r.html.render(sleep=2)
        response = r.html.html
        
        return response
        
    def create_soup_obj(self, response):
        
        soup = BeautifulSoup(response, 'html.parser')  # Use built-in parser
        details = soup.find_all('details')
        
        data = []
        for d in details:
            if 'POKEMON' in d.summary.text.upper():
                table = d.find_all('table')
                for t in table:
                    rows = t.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')   # td th
                        if cols:
                            data.append(cols)
        
        return data
    
    def find_csv(self, data):
        
        csv_dict = {}
        for row in data:
            print(row[0])
            for child in row[2].contents:
                if 'CSV' in child.text.upper():
                    # Here want to save the Href element of the tag
                    csv_endpoint = child.attrs["href"]
                    csv_dict[row[1].text] = {row[0].text: csv_endpoint}
        
        return csv_dict
    
    def parse_csv_data(self, csv_dict):
        
        csv_data = {}
        for set_id, set_info in csv_dict.items():
            for set_name, endpoint in set_info.items():
                # Construct full URL
                full_url = urljoin(self.url, endpoint)
                
                try:
                    response = requests.get(full_url, headers=self.headers)
                    response.raise_for_status()
                    
                    # Parse CSV content 
                    decoded_content = response.content.decode('utf-8')
                    csv_reader = csv.reader(decoded_content.splitlines())
                    rows = list(csv_reader)
                    
                    csv_data[set_name] = rows
                    print(f"Fetched {len(rows)} rows for {set_name}")
                                        
                except requests.exceptions.RequestException as e:
                    print(f"Failed to fetch {full_url}: {str(e)}")
                    
    
    def parser(self):
        
        response = self.render_js()
        
        data = self.create_soup_obj(response)
        
        csv_dict = self.find_csv(data)
        
        self.parse_csv_data(csv_dict)
        
        
        