import requests
from dotenv import load_dotenv
from datetime import datetime
import json
import os 
from app.pricing import positive_price

class TCGApi:
    
    def __init__(self, base_url="https://pokemon-tcg-api.p.rapidapi.com/"):
        
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_dotenv(os.path.join(self.BASE_DIR, '.env'))

        self.base_url = base_url
        self.token = os.getenv('TCG_BEARER')
        self.headers = {
            "x-rapidapi-key": os.getenv('TCG_BEARER'),
            "x-rapidapi-host": os.getenv('TCG_HOST'),
            "Content-Type": "application/json"
        }
        self.path_state = os.path.join(self.BASE_DIR, 'db', 'state.json')
        self.state = self.read_state(path=self.path_state)
        self.expansion_images_dir = os.path.join(self.BASE_DIR, 'images')
        
    def read_state(self, path):
        
        try:
            with open(path, 'r') as state_json:
                return json.load(state_json)
            
        except FileNotFoundError as e:
            raise e
        
    def update_state(self):
        """Update state"""
        
        self.state["last_run"] = str(datetime.now().strftime('%d-%m-%Y'))
        
        try:
            with open(self.path_state, 'w') as json_state:
                json.dump(self.state, json_state, indent=4)
                
        except Exception as e:
            raise e        
        
    def retrieve_cards_list(self):
        """Retrieve the top cards, tolerating missing optional data."""
        response = requests.get(
            self.base_url + f"episodes/{self.expansion.get('id')}/cards",
            headers=self.headers,
            params={"page": "1", "per_page": "30", "sort": "price_highest"},
        )
        response.raise_for_status()
        cards_list = response.json().get('data') or []
        os.makedirs(self.expansion_images_dir, exist_ok=True)
        cards_dict = {}
        for card in cards_list:
            name = card.get('name_numbered')
            image_url = card.get('image')
            if not name or not image_url:
                continue
            prices = card.get('prices') or {}
            tcg = prices.get('tcg_player') or {}
            cm = prices.get('cardmarket') or {}
            price = positive_price(tcg.get('market_price'))
            source = tcg
            if price is None:
                price = positive_price(cm.get('lowest_near_mint'))
                source = cm

            image_url = image_url.replace('\\/', '/')
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            # Keep generated filenames inside the image directory.
            filename = name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            image_path = os.path.join(self.expansion_images_dir, filename + '.png')
            with open(image_path, 'wb') as image_file:
                image_file.write(image_response.content)
            cards_dict[name] = {
                'imageUrl': image_url,
                'marketPrice': price if price is not None else 0,
                'currency': source.get('currency') or 'EUR',
                'imgPath': image_path,
            }
            if len(cards_dict) >= 20:
                break
        return dict(sorted(cards_dict.items(), key=lambda item: item[1]['marketPrice']))

    def get_expansion(self):
        """Retrieve a random expansion ID."""
        
        try:
            paging = 1
            while True:
                response = requests.get(self.base_url + "/episodes/", 
                                    headers=self.headers,
                                    params={
                                        "page": paging
                                    })
                
                if response.status_code == 200:
                    
                    data = response.json()
                    
                    for expansion in data.get('data', []):
                        
                        # Upcoming sets may have neither artwork nor cards. Counts are
                        # not reliable: released sets can also report cards_total=0.
                        if not expansion.get('logo'):
                            continue
                        released_at = expansion.get('released_at')
                        if released_at:
                            try:
                                if datetime.strptime(released_at, '%Y-%m-%d').date() > datetime.now().date():
                                    continue
                            except ValueError:
                                continue
                        if expansion.get('name') not in self.state.get('used_expansions', []):
                            
                            self.state.setdefault('used_expansions', []).append(expansion.get('name'))
                            self.update_state()
                            return expansion
                    
                    paging += 1
                    
                    if paging > data.get('paging', {}).get('total', 0): break
                else:
                    response.raise_for_status()
                            
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
            
    def get_detail_expansion(self):
        """Download the listing's logo without spending a detail API request."""
        logo_url = self.expansion.get('logo')
        if not logo_url:
            return None
        logo_url = logo_url.replace('\\/', '/')
        name = self.expansion.get('name') or str(self.expansion['id'])
        filename = name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        response = requests.get(logo_url)
        response.raise_for_status()
        os.makedirs(self.expansion_images_dir, exist_ok=True)
        path = os.path.join(self.expansion_images_dir, filename + '_LOGO.png')
        with open(path, 'wb') as image_file:
            image_file.write(response.content)
        return path

    def get_cards_expansion(self):
        """Get the cards from the expansion."""

        self.check_state()

        while True:
            self.expansion = self.get_expansion()

            if not self.expansion:
                raise Exception("No more unused expansions available.")

            self.expansion_image_path = self.get_detail_expansion()
            if not self.expansion_image_path:
                continue
            self.cards = self.retrieve_cards_list()

            if len(self.cards) >= 15:
                break

        return self.expansion, self.cards, self.expansion_image_path
        