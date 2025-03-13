import requests
from bs4 import BeautifulSoup
import os 
import time
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
        r.html.render()
        response = r.html.html
        
        return response
        
    def create_soup_obj(self, response):
        
        soup = BeautifulSoup(response, 'html.parser')  # Use built-in parser
        summary = soup.find_all('summary')
        
        return soup
        
    
    def download_csv(self):
        pass
    
    def parser(self):
        
        response = self.render_js()
        
        soup = self.create_soup_obj(response)
        
        content = self.find_csv_content(soup)
        