import sqlite3
import requests

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
                ORDER BY marketPrice DESC
                LIMIT 10
            """, (set_name)
            )
            
            return self.cursor.fetchall()
            
        def process_cards(self, cards_list):
            """
            Create a picture of each card with the market price on it. 

            Args:
                cards_list (_type_): _description_
            """
            
        def build_clip(self):
            """
            
            """
            
            card_list = self.query_cards('')