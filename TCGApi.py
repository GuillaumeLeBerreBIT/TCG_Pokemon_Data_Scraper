import requests
from dotenv import load_dotenv
import os 

class TCGApi:
    
    def __init__(self):
        
        load_dotenv('.env')
                
        self.base_url = "https://pokemon-tcg-api.p.rapidapi.com/"
        self.token = os.getenv('TCG_BEARER')
        self.headers = {
            "x-rapidapi-key": os.getenv('TCG_BEARER'),
            "x-rapidapi-host": "pokemon-tcg-api.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        
    def retrieve_expansions(self):
        """Get a list of alle expansions"""
        try:
            
            response = requests.get(self.base_url + "episodes/", headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            
            else:
                raise requests.exceptions.ConnectionError('Problem downloading the expansions for Pokemon.')
            
        except requests.exceptions.RequestException as e:
            
            print('Problem retrieving all expansions list for pokemon cards: ', e)
        
    def retrieve_cards_list(self, expansion_id):
        """Retrieve all cards from the expansion"""
        try:
            
            response = requests(self.base_url + f"episodes/{expansion_id}/cards", headers=self.headers)
            
            if response.status_code == 200:
                return response.json()

            else:
                raise requests.exceptions.ConnectionError('Problem downloading the expansions for Pokemon.')
            
        except requests.exceptions.RequestException as e:
            print('Problem retrieving all expansions list for pokemon cards: ', e)
            
            
    def get_random_expansion(self, data):
        """Retrieve a random expansion ID."""
        
    
    def retrieve_expensive_cards(self):
        """Retrieve the most expensive cards of an expansion."""