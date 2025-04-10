import sqlite3
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import random
from moviepy import ImageClip, concatenate_videoclips
# Import the proper fade effects
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from moviepy.video.compositing import CompositeVideoClip
from moviepy import *
from datetime import datetime
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
        os.makedirs('expansion_images', exist_ok=True)
        
        self.expansion_images_dir = './expansion_images/'
        
        #Portrait sizes
        self.width = 1080
        self.height = 1980
        
    def get_expansion_name(self):
        """
        Get a random Image name from the expansion list.
        """
        
        expansion_images = [img for img in os.listdir(self.expansion_images_dir) if img.endswith('.jpg') or img.endswith('.png')]
        
        expansion_image = random.choice(expansion_images)
        
        if '-' in expansion_image:
            expansion_raw_name = expansion_image.split('-')[1]
        elif '-' not in expansion_image:
            expansion_raw_name = expansion_image
            
        if expansion_raw_name.startswith('EX_'): expansion_raw_name = expansion_raw_name.replace('EX_', '')
        
        expansion_name = os.path.splitext(expansion_raw_name)[0]     
        
        return os.path.join(self.expansion_images_dir, expansion_image), expansion_name.replace('_', ' ')
    
    def get_background_image(self):
        """
        Get the background image for all the cards.
        """
        
        images = [f for f in os.listdir('./backgrounds') if f.endswith(('.jpg', '.png'))]
        
        return os.path.join('./backgrounds', random.choice(images))
        
                
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
            AND (marketPrice IS NOT '' OR midPrice is NOT '')
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
                # Here already in Bytes can direclty save it to BytesIO
                img_bytes = BytesIO(response.content)
                price = marketPrice if marketPrice else midPrice
                cards_dictionary[int(price)] = {
                    'imageUrl': imageUrl,
                    'lowPrice': lowPrice,
                    'midPrice': midPrice,
                    'highPrice': highPrice,
                    'marketPrice': marketPrice,
                    'name': name,
                    'imgBytes': img_bytes,
                }

        return dict(sorted(cards_dictionary.items()))
    
    def create_header_image(self, background_path, expansion_path):
        """
        Creates a header image with the expansion logo centered on a background
        
        Args:
            background_path: Path to background image
            expansion_path: Path to expansion logo image
        """
        # Load and resize background to portrait dimensions
        background_img = Image.open(background_path)
        background_img = background_img.resize((self.width, self.height), Image.LANCZOS)
        
        # Load expansion image
        expansion_image = Image.open(expansion_path)
        
        # Calculate sizes to maintain aspect ratio
        expansion_width = int(self.width * 0.95)
        expansion_height = int(expansion_width * (expansion_image.height / expansion_image.width))
        expansion_image_res = expansion_image.resize((expansion_width, expansion_height), Image.LANCZOS)
        
        # Center the expansion image on the background
        x_offset = (self.width - expansion_width) // 2
        y_offset = (self.height - expansion_height) // 2
        
        # Create a copy of the background to work with
        final_img = background_img.copy()
        
        if expansion_image_res.mode == 'RGBA':
            # Paste the expansion image onto the background >> USe the orignal expansion image as Mask source value.
            # If the background if the image has an alpha value of 0 then it will be ignored during the pasting. Otherwise 255 will be complete Opaque.
            final_img.paste(expansion_image_res, (x_offset, y_offset), expansion_image_res)
        else:
            final_img.paste(expansion_image_res, (x_offset, y_offset))
        # Create drawing context on the FINAL image (not the expansion image)
        draw = ImageDraw.Draw(final_img)
        
        try:
            # Load a font type specific to Pokemon styled theme
            font_type_large = ImageFont.truetype('./font/Bangers-Regular.ttf', 150)
        except IOError:
            font_type_large = ImageFont.load_default()
        
        # Set text colors
        fillcolor = (255, 255, 255)
        shadowcolor = 'black'
        
        # Get current month and year
        current_date = datetime.now()
        date_string = current_date.strftime("%B %Y")
        
        # Create the header text
        header_text = f"Prices {date_string}"
        
        # Calculate text position (centered horizontally, near top vertically)
        text_width = draw.textlength(header_text, font=font_type_large)
        x = (self.width - text_width) // 2
        y = 500  # Top margin
        
        # Add text with border effect to the final image
        self.create_text_border(draw, x, y, font_type_large, header_text, fillcolor, shadowcolor)
        
        header_image_path = './card_images/expansion_image.jpg'
        # Save as RGB (removing alpha channel if present)
        final_img = final_img.convert('RGB')
        final_img.save('./temp/images/expansion_image.jpg')
        
        return header_image_path
    
    def create_ending_image(self):
        """
        Create the last image to displat int he cards list. 
        """
        
        pass
        
            
    def process_cards(self, cards_dict, background_image):
        """
        Create a picture of each card with the market price on it.

        Args:
            cards_dict (dict): Dictionary of card details
        
        Returns:
            list: List of paths to processed card images
        """
        
        # Load background image and apply blur
        background_img = Image.open(background_image)
        blurred_background = background_img.filter(ImageFilter.GaussianBlur(radius=10))
        blurred_background = blurred_background.resize((self.width, self.height), Image.LANCZOS)
        
        try:
            # Load a font type specific to Pokemon styled theme
            font_type_large = ImageFont.truetype('./font/Bangers-Regular.ttf', 120)
        except IOError:
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
            card_count = len(cards_dict.keys()) - i
            
            # Resize card image to fit nicely on background
            card_width = int(self.width * 0.8)
            card_height = int(card_width * (card_img.height / card_img.width))
            card_img_resized = card_img.resize((card_width, card_height), Image.LANCZOS)
            
            # Create a new image with blurred background
            final_img = blurred_background.copy()
            
            # Calculate position to center the card
            x_offset = (self.width - card_width) // 2
            y_offset = (self.height - card_height) // 2
            
            # Paste the card onto the background
            final_img.paste(card_img_resized, (x_offset, y_offset))
            
            # Create a drawing context
            draw = ImageDraw.Draw(final_img)
            
            name = f'#{card_count} {name}'
            
            # Add card name with border
            name_width = draw.textlength(name, font=font_type_large)
            
            self.create_text_border(draw, (self.width - name_width) // 2, 220, font_type_large, name, fillcolor, shadowcolor)
            
            # # Add market price
            price = card['marketPrice'] if card['marketPrice'] else card['midPrice']
            price_text = f"Market Price: ${price:.2f}"
            price_width = draw.textlength(price_text, font=font_type_large)
            
            self.create_text_border(draw, (self.width - price_width) // 2,  self.height - 300, font_type_large, price_text, fillcolor, shadowcolor)
            
            # Save the final image > remove backslashes otherwise incomplete paths. 
            output_path = f'card_images/{name.replace('/', '-')}_PRICE_CARD.jpg'
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
        # Draw border (8 surrounding positions) > Stretch the text out on all sides to create a border.
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
        
    def create_composite_clip(self, processed_images, set_name):
        """
        Create a full clip using all processed images. 

        Args:
            processed_images (_type_): _description_    
        """
        # Define duration parameters
        clip_duration = 7  # Seconds each clip stays (including fade time)
        fade_duration = 1  # Seconds for fade effects

        clips = []
        
        header_clip = ImageClip('./temp/images/expansion_image.jpg').with_duration(clip_duration)
        header_clip = CrossFadeIn(fade_duration).apply(header_clip)
        header_clip = CrossFadeOut(fade_duration).apply(header_clip)
        
        clips.append(header_clip)
        
        for i, img_path in enumerate(processed_images):
            # Need to take in advance the header image
            i += 1
            # Create base clip with full duration
            clip = ImageClip(img_path).with_duration(clip_duration)
            
            # Apply transitions conditionally
            clip = CrossFadeIn(fade_duration).apply(clip)
            if i < len(processed_images)-1:  # Only apply fade-out to non-last clips
                clip = CrossFadeOut(fade_duration).apply(clip)
            
            # Calculate staggered start time with overlap
            start_time = i * (clip_duration - fade_duration)
            
            # Position clip in composition
            clip = clip.with_start(start_time)
            clips.append(clip)

        # Create final composite with overlapping clips
        final_video = CompositeVideoClip(clips)

        # Calculate total duration properly
        total_duration = len(processed_images)*(clip_duration-fade_duration) + clip_duration
        final_video = final_video.with_duration(total_duration)
        
        audio_path = self.get_audio(total_duration)
        
        final_video = final_video.with_audio(AudioFileClip(audio_path).subclipped(0, total_duration))
        
        # Write the final video
        final_video.write_videofile(f'final_video/top_10_pokemon_cards_{set_name.replace(' ', '_')}.mp4', fps=24)
        
    def get_audio(self, total_duration):
        """
        Find the audio file to add onto the Composite video clip.

        Args:
            total_duraiton (_type_): _description_
        """
        
        music_folder = [s for s in os.listdir('./music/') if s.endswith('.mp4')]
        
        if music_folder:
            
            song_path = os.path.join('./music/', random.choice(music_folder))
            song, _ = os.path.splitext(os.path.basename(song_path))
            
            if song_path.endswith('.mp4'):
                
                video = VideoFileClip(song_path)
                audio = video.audio
                audio_path = f'./temp/music/{song}.mp3'
                audio.write_audiofile(audio_path)
                video.close()
                
            else:
                audio = AudioClip(song_path)
            
            # Adjust the audio duration
            if audio.duration < total_duration:
                
                repeats = int(total_duration // audio.duration) + 1
                audio_segments = repeats * [audio]
                
                from moviepy import concatenate_audioclips
                looped_audio = concatenate_audioclips(audio_segments)
                audio = looped_audio.subclipped(0, total_duration)
            
            else:
                
                audio = audio.subclipped(0, total_duration)
                
            return audio_path
                
        
    def build_clip(self):
        """
        Create a one minute long clip of pokemon cards.
        """
        cards_list = []
        # Load in a set to create the video from
        while not cards_list or len(cards_list) < 10:
            # Get the set_name based on a image.
            expansion_image, set_name = self.get_expansion_name()
            # Retrieve the 
            cards_list = self.query_cards(set_name)
        
        # Background image
        background_image = self.get_background_image()
            
        self.create_header_image(background_image, expansion_image)
        
        # Download images
        cards_dictionary = self.download_images(cards_list)
        
        # Process cards and get image paths
        processed_images = self.process_cards(cards_dictionary, background_image)
        
        self.create_composite_clip(processed_images, set_name)

        
    def __close__(self):
        """
        Close database connection
        """
        self.conn.close()

if __name__ == '__main__':
    
    video_creation = VideoCreation()
    video_creation.build_clip()