import sqlite3
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from moviepy import ImageClip, concatenate_videoclips
# Import the proper fade effects
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from moviepy.video.compositing import CompositeVideoClip

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
                cards_dictionary[int(marketPrice)] = {
                    'imageUrl': imageUrl,
                    'lowPrice': lowPrice,
                    'midPrice': midPrice,
                    'highPrice': highPrice,
                    'marketPrice': marketPrice,
                    'name': name,
                    'imgBytes': img_bytes,
                }

        return dict(sorted(cards_dictionary.items()))
            
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
        # Get the size of the background.
        b_width, b_height = blurred_background.size
        
        try:
            # Load a font type specific to Pokemon styled theme
            font_type_small = ImageFont.truetype('./font/Bangers-Regular.ttf', 40)
            font_type_large = ImageFont.truetype('./font/Bangers-Regular.ttf', 70)
        except IOError:
            font_type_small = ImageFont.load_default()
            font_type_large = ImageFont.load_default()
            
        fillcolor = (255,255,255)
        shadowcolor = 'green'
        
        processed_images = []
        
        for i, (market_price, card) in enumerate(cards_dict.items()):
            # Open the card image >> IN Bytes
            card_img = Image.open(card['imgBytes'])
            # Get the name of the Image
            name = card['name']
            # Get the count
            card_count = 10 - i
            
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
            
            name = f'#{card_count} {name}'
            
            # Add card name with border
            name_width = draw.textlength(name, font=font_type_large)
            
            self.create_text_border(draw, (b_width - name_width) // 2, 200, font_type_large, name, fillcolor, shadowcolor)
            
            # # Add market price
            price_text = f"Market Price: ${card['marketPrice']:.2f}"
            price_width = draw.textlength(price_text, font=font_type_large)
            
            self.create_text_border(draw, (b_width - price_width) // 2,  b_height - 300, font_type_large, price_text, fillcolor, shadowcolor)
            
            # Save the final image
            output_path = f'card_images/{name}_price.jpg'
            final_img.save(output_path)
            processed_images.append(output_path)
        
        return processed_images
    
    def create_text_border(self, draw, x, y, font, text, text_color, shadow_color):
        """
        Generate a border around the text displayed on the image.

        Args:
            draw (_type_): _description_
            x (_type_): _description_
            y (_type_): _description_
            font (_type_): _description_
            text (_type_): _description_
            text_color (_type_): _description_
            shadow_color (_type_): _description_
        """
        # Draw border (8 surrounding positions)
        draw.text((x - 4, y), text, font=font, fill=shadow_color)  # Left
        draw.text((x + 4, y), text, font=font, fill=shadow_color)  # Right
        draw.text((x, y - 4), text, font=font, fill=shadow_color)  # Up
        draw.text((x, y + 4), text, font=font, fill=shadow_color)  # Down
        draw.text((x - 4, y - 4), text, font=font, fill=shadow_color)  # Top-left
        draw.text((x + 4, y - 4), text, font=font, fill=shadow_color)  # Top-right
        draw.text((x - 4, y + 4), text, font=font, fill=shadow_color)  # Bottom-left
        draw.text((x + 4, y + 4), text, font=font, fill=shadow_color)  # Bottom-right

        # Draw main text on top
        draw.text((x, y), text, font=font, fill=text_color)
        
    def build_clip(self):
        """
        Create a one minute long clip of pokemon cards.
        """
        
        # Load in a set to create the video from
        set_name = 'Base Set'
        
        # Query cards
        cards_list = self.query_cards('Base Set')
        
        # Download images
        cards_dictionary = self.download_images(cards_list)
        
        # Process cards and get image paths
        processed_images = self.process_cards(cards_dictionary)
        
        # Define duration parameters
        clip_duration = 6  # seconds each card stays on screen
        fade_duration = 1  # seconds for fade effects
        
        # Initialize fade effect classes
        crossfadein = CrossFadeIn(fade_duration)
        crossfadeout = CrossFadeOut(fade_duration)
        
        # Create video clips with both cross fade in and fade out effects
        clips = []
        for img_path in processed_images:
            # Create clip with duration
            clip = ImageClip(img_path).with_duration(clip_duration)
            
            # Apply CrossFadeIn effect
            clip = crossfadein.apply(clip)
            
            # Apply FadeOut effect
            clip = crossfadeout.apply(clip)
            
            clips.append(clip)
        
        # Concatenate clips in sequence
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Write the final video
        final_video.write_videofile(f'final_video/top_10_pokemon_cards_{set_name.replace(' ', '_')}.mp4', fps=30)
        
    def __del__(self):
        """
        Close database connection
        """
        self.conn.close()

if __name__ == '__main__':
    
    video_creation = VideoCreation()
    video_creation.build_clip()