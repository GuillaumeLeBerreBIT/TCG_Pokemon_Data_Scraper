import requests
from dotenv import load_dotenv
from datetime import datetime
import json
import os 

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
        self.path_fx = os.path.join(self.BASE_DIR, 'db', 'fx_rate.json')
        self.eur_usd = self.get_eur_usd_rate()

    # The upstream API reports tcg_player.market_price in EUR (prices.tcg_player.currency
    # is literally "EUR"), even though TCGPlayer itself quotes USD. Verified against
    # pokemontcg.io's native TCGPlayer feed over 60 cards: median ratio 1.1695 vs the
    # ECB EUR/USD rate of 1.1699. Without this conversion every price we render is ~14%
    # below what a viewer sees on TCGPlayer or Collectr.
    FX_FALLBACK = 1.17

    def get_eur_usd_rate(self):
        """Return EUR->USD, from a once-per-day cached ECB rate."""

        today = datetime.now().strftime('%d-%m-%Y')

        try:
            with open(self.path_fx, 'r') as f:
                cached = json.load(f)
            if cached.get('date') == today and cached.get('rate'):
                return float(cached['rate'])
        except (FileNotFoundError, ValueError, KeyError):
            pass

        try:
            response = requests.get('https://api.frankfurter.dev/v1/latest',
                                    params={'base': 'EUR', 'symbols': 'USD'},
                                    timeout=10)
            response.raise_for_status()
            rate = float(response.json()['rates']['USD'])

            with open(self.path_fx, 'w') as f:
                json.dump({'date': today, 'rate': rate}, f, indent=4)

            return rate

        except Exception as e:
            print(f'Could not fetch EUR/USD rate ({e}); falling back to {self.FX_FALLBACK}')
            return self.FX_FALLBACK

    def to_usd(self, amount_eur):
        """Convert an EUR figure from the API into the USD we display."""

        try:
            return round(float(amount_eur) * self.eur_usd, 2)
        except (TypeError, ValueError):
            return None

    # eBay medians are already USD (prices.ebay.currency == "USD"), so unlike the
    # Cardmarket figures these need no conversion. Coverage is uneven on freshly
    # released sets, where a "median" can rest on a single sale.
    PSA10_MIN_SAMPLES = 5

    def get_psa10_price(self, card):
        """PSA 10 median sold price in USD, or None when the sample is too thin to trust."""

        entry = (((card.get('prices', {}).get('ebay') or {}).get('graded') or {})
                 .get('psa') or {}).get('10') or {}

        if (entry.get('sample_size') or 0) < self.PSA10_MIN_SAMPLES:
            return None

        try:
            return round(float(entry['median_price']), 2)
        except (TypeError, ValueError, KeyError):
            return None

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
        """Retrieve all cards from the expansion"""
        
        def download_image(url, name):
            
            try:
                response = requests.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    
                    card_image_path = f"{self.expansion_images_dir}/{name}.png"
                    
                    with open(card_image_path, 'wb') as f:
                        f.write(response.content)
                    
                    return card_image_path
                
            except Exception as e:
                raise e
            
        # The API's sort=price_highest ranks by Cardmarket's lowest_near_mint, not by the
        # TCGPlayer market price we actually display, so the two orderings disagree. Pull a
        # wider candidate pool than we need and re-rank on our own price below.
        cards_list = []
        try:
            for page in (1, 2):
                response = requests.get(self.base_url + f"episodes/{self.expansion.get('id')}/cards",
                                    headers=self.headers,
                                    params={"page": str(page), "per_page": "30", "sort": "price_highest"})

                if response.status_code != 200:
                    break

                page_cards = response.json().get('data', [])

                if not page_cards:
                    break

                cards_list += page_cards

        except requests.exceptions.RequestException as e:
            print('Problem retrieving all expansions list for pokemon cards: ', e)

        try:
            # Price and rank first, download images only for the cards that make the cut.
            priced = []
            for card in cards_list:
                price_usd = self.to_usd(card.get('prices', {}).get('tcg_player', {}).get('market_price'))

                # No fallback to Cardmarket's lowest_near_mint here: that is the cheapest
                # standing listing in EUR, a different metric from a market price. Mixing
                # the two silently prints a wrong number under a "$" sign.
                if not price_usd:
                    continue

                priced.append((card, price_usd))

            top_cards = sorted(priced, key=lambda item: item[1], reverse=True)[:20]

            # Ascending so the video counts down to the most expensive card last.
            cards_dict = {}
            for card, price_usd in sorted(top_cards, key=lambda item: item[1]):
                image_url = card.get('image').replace('\\/', '/')
                image_path = download_image(image_url, card.get('name_numbered').replace(' ', '_'))

                cards_dict[card.get('name_numbered')] = {
                    'imageUrl': image_url,
                    'marketPrice': price_usd,
                    'psa10Price': self.get_psa10_price(card),
                    'imgPath': image_path
                }

            return cards_dict

        except Exception as e:

            return {}
            
            
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
                        
                        if expansion.get('name') not in self.state.get('used_expansions', []):
                            
                            self.state.get('used_expansions', []).append(expansion.get('name'))
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
        
        try:
            response = requests.get(self.base_url + f"episodes/{self.expansion.get('id')}", 
                                headers=self.headers)

            logo_url = response.json().get('data', {}).get('logo', '').replace('\\/', '/')
            expansion_name = response.json().get('data', {}).get('name', '').replace(' ', '_')
            
            if not logo_url: raise Exception('No Logo found for this expansion set.')
            
        except Exception as e:
            raise e
        
        try:
            response = requests.get(logo_url, headers=self.headers)
            
            if response.status_code == 200:
                
                os.makedirs(self.expansion_images_dir, exist_ok=True)
                
                expansion_path = f'{self.expansion_images_dir}/{expansion_name}_LOGO.png'
                
                with open(expansion_path, 'wb') as f:
                    f.write(response.content)
                
                return expansion_path
            
        except Exception as e:
            raise e
    
        
    def get_cards_expansion(self):
        """Get the cards from the expansion."""

        self.check_state()

        while True:
            self.expansion = self.get_expansion()

            if not self.expansion:
                raise Exception("No more unused expansions available.")

            self.expansion_image_path = self.get_detail_expansion()
            self.cards = self.retrieve_cards_list()

            if len(self.cards) >= 15:
                break

        return self.expansion, self.cards, self.expansion_image_path
        