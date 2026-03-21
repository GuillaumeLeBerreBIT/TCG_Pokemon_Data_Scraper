import requests
from dotenv import load_dotenv
from datetime import datetime
import json
import os 

class TCGApi:
    
    def __init__(self, base_url="https://pokemon-tcg-api.p.rapidapi.com/"):
        
        load_dotenv('.env')
                
        self.base_url = base_url
        self.token = os.getenv('TCG_BEARER')
        self.headers = {
            "x-rapidapi-key": os.getenv('TCG_BEARER'),
            "x-rapidapi-host": os.getenv('TCG_HOST'),
            "Content-Type": "application/json"
        }
        self.path_state="./db/state.json"
        self.state = self.read_state(path=self.path_state)
        
    def read_state(self, path="./db/state.json"):
        
        try:
            with open(path, 'r') as state_json:
                return json.load(state_json)
            
        except FileNotFoundError as e:
            raise e
        
    def update_state (self, path="./db/state.json"):
        """Update state"""
        
        self.state["last_run"] = str(datetime.now().strftime('%d-%m-%Y'))
        
        try:
            with open(self.path_state, 'w') as json_state:
                json.dump(self.state, json_state, indent=4)
                
        except Exception as e:
            raise e        
        
    def retrieve_cards_list(self):
        """Retrieve all cards from the expansion"""
        try:
            querystring = {"page":"1","per_page":"20","sort":"price_highest"}

            response = requests.get(self.base_url + f"episodes/{self.expansion.get('id')}/cards", 
                                headers=self.headers,
                                params=querystring)
            
            if response.status_code == 200:
                
                return response.json().get('data', [])
                
            
        except requests.exceptions.RequestException as e:
            print('Problem retrieving all expansions list for pokemon cards: ', e)
            
            
    def get_expansion(self):
        """Retrieve a random expansion ID."""
        
        try:
            paging = 1
            while True:
                response = requests.get(self.base_url + "/episodes/", 
                                    headers=self.headers,
                                    params={
                                        "paging": paging
                                    })
                
                if response.status_code == 200:
                    
                    data = response.json()
                    
                    for expansion in data.get('data', []):
                        
                        if expansion.get('name') not in self.state.get('used_expansions', []):
                            
                            self.state.get('used_expansions', []).append(expansion.get('name'))
                            self.update_state()
                            return expansion
                    
                    paging += 1
                    
                    if paging > data.get('paging', {}).get('total', 0): break

                response.raise_for_status()
                
            raise Exception('Unable to find an expansion that has not been processed')
            
        except requests.exceptions.RequestException as e:
            print('Problem retrieving all expansions list for pokemon cards: ', e)
        
    
    def retrieve_expensive_cards(self):
        """Retrieve the most expensive cards of an expansion."""
        
    def check_state(self):
        
        try:
            last_run = self.state.get('last_run')
            
            if not last_run:
                return
            
            last_run_obj = datetime.strptime(last_run, '%d-%m-%Y')
            today = datetime.now()
            
            if today.month == 1:
                prev_month = 12
                prev_year = today.year - 1
            else:
                prev_month = today.month -1
                prev_year = today.year
                
            is_previous_month = (last_run_obj.month == prev_month and last_run_obj.year == prev_year)
            
            if is_previous_month:
                self.state['used_expansions'] = []
            
        except Exception as e:
            print(e)
        
    def get_cards_expansion(self):
        """Get the cards from the expansion."""
        
        self.check_state()
        
        self.expansion = self.get_expansion()
        
        self.cards = self.retrieve_cards_list()
        
        return self.expansion, self.cards[:10]
        