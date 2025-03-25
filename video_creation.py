import sqlite3
import requests
from io import BytesIO

class VideoCreation:
    
    def __init__(self):
        """
        
        """
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        self.db = 'pokemontcg.db'
        
        # Initialize database
        self.conn = sqlite3.connect(self.db)
        self.cursor = self.conn.cursor()
        
    def query_cards(self, set_name):
        """
        Querry the database for the top 10 most expensive cards for a Set. 

        Args:
            set_name (_type_): _description_
        """
        
        self.cursor.execute("""
            SELECT name, imageUrl, lowPrice, midPrice, highPrice, marketPrice
            FROM pokemon 
            WHERE setName = ? 
            AND extNumber IS NOT '' 
            AND extCardType IS NOT ''
            ORDER BY marketPrice DESC
            LIMIT 10
        """, (set_name,)
        )
        
        return self.cursor.fetchall()
    
    def download_images(self, cards_list):
        """
        Donwload the images
        """
        cards_dictionary = {}
        for card in cards_list:
            
            name, imageUrl, lowPrice, midPrice, highPrice, marketPrice = card
            
            response = requests.get(url=card[1], headers=self.headers)
            
            if response.status_code == 200:
                img_bytes = BytesIO(response.content)
                cards_dictionary[name] = {
                    'imageUrl': imageUrl,
                    'lowPrice': lowPrice,
                    'midPrice': midPrice,
                    'highPrice': highPrice,
                    'marketPrice': marketPrice,
                    'imgBytes': img_bytes,
                }
                
        return cards_dictionary
            
        
    def process_cards(self, cards_dict):
        """
        Create a picture of each card with the market price on it. 

        Args:
            cards_list (_type_): _description_
        """
        
    def build_clip(self):
        """
        Create a one minute long clip of pokemon cards. 
        """
        
        cards_list = self.query_cards('Base Set')
        
        cards_dictionary = self.download_images(cards_list)
        
        self.process_cards(cards_dictionary)
            
if __name__ == '__main__':
    
    video_creation = VideoCreation()
    video_creation.build_clip()