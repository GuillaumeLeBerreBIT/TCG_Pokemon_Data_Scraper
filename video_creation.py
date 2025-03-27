import sqlite3
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from moviepy import ImageClip, concatenate_videoclips

class VideoCreation:
    
    def __init__(self):
        """
        Initialize the video creation process
        """
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        self.db = 'pokemontcg.db'
        
        # Initialize database
        self.conn = sqlite3.connect(self.db)
        self.cursor = self.conn.cursor()
        
        # Ensure output directories exist
        os.makedirs('card_images', exist_ok=True)
        os.makedirs('final_video', exist_ok=True)
        
    def query_cards(self, set_name):
        """
        Query the database for the top 10 most expensive cards for a Set.

        Args:
            set_name (str): Name of the Pokémon card set
        
        Returns:
            list: List of card details
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
        Download the images for the cards

        Args:
            cards_list (list): List of card details
        
        Returns:
            dict: Dictionary of card details with downloaded images
        """
        cards_dictionary = {}
        for card in cards_list:
            
            name, imageUrl, lowPrice, midPrice, highPrice, marketPrice = card
            
            response = requests.get(url=imageUrl, headers=self.headers)
            
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
            cards_dict (dict): Dictionary of card details
        
        Returns:
            list: List of paths to processed card images
        """
        
        # Load background image and apply blur
        background_img = Image.open('backgrounds/pokemon_town_background_1.jpg')
        blurred_background = background_img.filter(ImageFilter.GaussianBlur(radius=10))
        b_width, b_height = blurred_background.size
        
        # Prepare font
        try:
            font_large = ImageFont.truetype("arial.ttf", 50)
            font_small = ImageFont.truetype("arial.ttf", 30)
        except IOError:
            # Fallback to default font if Arial is not available
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        processed_images = []
        
        for name, card in cards_dict.items():
            # Open the card image
            card_img = Image.open(card['imgBytes'])
            
            # Resize card image to fit nicely on background
            card_width = int(b_width * 0.6)
            card_height = int(card_width * (card_img.height / card_img.width))
            card_img_resized = card_img.resize((card_width, card_height), Image.LANCZOS)
            
            # Create a new image with blurred background
            final_img = blurred_background.copy()
            
            # Calculate position to center the card
            x_offset = (b_width - card_width) // 2
            y_offset = (b_height - card_height) // 2
            
            # Paste the card onto the background
            final_img.paste(card_img_resized, (x_offset, y_offset))
            
            # Create a drawing context
            draw = ImageDraw.Draw(final_img)
            
            # Add card name
            name_width = draw.textlength(name, font=font_large)
            draw.text(((b_width - name_width) // 2, 50), name, font=font_large, fill=(255,255,255))
            
            # Add market price
            price_text = f"Market Price: ${card['marketPrice']:.2f}"
            price_width = draw.textlength(price_text, font=font_small)
            draw.text(((b_width - price_width) // 2, b_height - 100), 
                      price_text, font=font_small, fill=(255,255,255))
            
            # Save the final image
            output_path = f'card_images/{name}_price.jpg'
            final_img.save(output_path)
            processed_images.append(output_path)
        
        return processed_images
        
    def build_clip(self):
        """
        Create a one minute long clip of pokemon cards.
        """
        
        # Query cards
        cards_list = self.query_cards('Base Set')
        
        # Download images
        cards_dictionary = self.download_images(cards_list)
        
        # Process cards and get image paths
        processed_images = self.process_cards(cards_dictionary)
        
        # Create video clips
        clips = [
            ImageClip(img).with_duration(6)  # 6 seconds per card to make 60 seconds total
            for img in processed_images
        ]
        
        # Concatenate clips
        final_video = concatenate_videoclips(clips)
        
        # Write the final video
        final_video.write_videofile('final_video/top_10_pokemon_cards.mp4', fps=24)
        
    def __del__(self):
        """
        Close database connection
        """
        self.conn.close()

if __name__ == '__main__':
    
    video_creation = VideoCreation()
    video_creation.build_clip()