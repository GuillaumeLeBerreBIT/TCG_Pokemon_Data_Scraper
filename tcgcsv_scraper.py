import requests
from bs4 import BeautifulSoup

class TCGCSVScraper:
    
    def __init__(self):
        
        self.url = 'https://tcgcsv.com/'
        self.headers= {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        
    def create_soup_obj(self):
        response = requests.get(self.url, headers=self.headers)  # Corrected request call
        if response.status_code == 200:  # Check if request was successful
            soup = BeautifulSoup(response.text, 'html.parser')  # Use built-in parser
            return soup
        else:
            print(f"Error: Unable to fetch page, status code {response.status_code}")
            return None
    
    def download_csv(self):
        pass
    
    def parser(self):
        self.create_soup_obj()
        