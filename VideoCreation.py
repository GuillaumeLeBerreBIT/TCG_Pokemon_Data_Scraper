import sqlite3
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import random
from thefuzz import process
from moviepy import ImageClip
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from moviepy.video.compositing import CompositeVideoClip
from moviepy import *
from datetime import datetime
import math

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
        self.temp_folder = './temp/'
        
        #Portrait sizes
        self.width = 1080
        self.height = 1980
        
        self.background_image = None
        self.header_image_path = './temp/images/{}_EXPANSION_IMAGE.jpg'
        self.ending_image_path = './temp/images/{}_{}_ENDING.jpg'
        
        try:
            # Load a font type specific to Pokemon styled theme
            self.font_type_large = ImageFont.truetype('./font/Bangers-Regular.ttf', 150)
            self.font_type_cards = ImageFont.truetype('./font/Bangers-Regular.ttf', 120)
        except IOError:
            self.font_type_large = ImageFont.load_default(size=150)
            self.font_type_cards = ImageFont.load_default(size=120)
        
        self.fillcolor = (255, 255, 255)
        self.shadowcolor_headers = 'black'
        self.shadowcolor_cards = 'green'
        
         # Define duration parameters
        self.clip_duration = 6  # Seconds each clip stays (including fade time)
        self.fade_duration = 1  # Seconds for fade effects
        
    def get_expansion_name(self, expansion=None):
        """
        Get a random Image name from the expansion list.
        """
            
        expansion_images = [img for img in os.listdir(self.expansion_images_dir) if img.endswith('.jpg') or img.endswith('.png')]
        
        if expansion:
            
            name_mappings = []
            for img in expansion_images:
                
                # Get the full name first
                full_display_name = os.path.splitext(img)[0].replace('_', ' ')
                
                if '-' in img:
                    raw_name = img.split('-', 1)[1]
                else:
                    raw_name = img
                    
                name_without_extension, _ = os.path.splitext(raw_name)
                if name_without_extension.startswith('EX'):
                    name_without_extension = name_without_extension.replace('EX_', '').strip()
                    
                partial_display_name = name_without_extension.replace('_', ' ')
                
                name_mappings.append((img, full_display_name, partial_display_name))
                
            full_names  = [full for _, full, _ in name_mappings]
            best_full_match = process.extractOne(expansion, full_names)
            
            partial_names = [partial for _, _, partial in name_mappings]
            best_partial_match = process.extractOne(expansion, partial_names)
            
            if (best_full_match and best_partial_match and 
                best_full_match[1] > best_partial_match[1]):
                matched_image = next((img for img, full, _ in name_mappings
                                        if best_full_match[0] == full), None)
                
            elif best_partial_match:
                matched_image = next((img for img, _, partial in name_mappings
                                        if best_partial_match[0] == partial), None)
            
            else:
                matched_image = None
                
            if matched_image:
                expansion_image = matched_image
            else:
                expansion_image = random.choice(expansion_images)
                
        else:
    
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
        rows = self.cursor.fetchall()
        
        if not rows:
            like_pattern = f'%{set_name}%'
            self.cursor.execute("""
                SELECT name, imageUrl, lowPrice, midPrice, highPrice, marketPrice
                FROM pokemon 
                WHERE setName LIKE ? 
                AND extNumber IS NOT '' 
                AND extCardType IS NOT ''
                AND (marketPrice IS NOT '' OR midPrice is NOT '')
                ORDER BY marketPrice DESC
                LIMIT 10
            """, (like_pattern,)
            )
            rows = self.cursor.fetchall()
        
        return rows
    
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
                # price = marketPrice if marketPrice else midPrice
                cards_dictionary[name] = {
                    'imageUrl': imageUrl,
                    'lowPrice': lowPrice,
                    'midPrice': midPrice,
                    'highPrice': highPrice,
                    'marketPrice': marketPrice,
                    'imgBytes': img_bytes,
                }
        # The sort will place them from lowest number to high
        # Key [0] will acces the key, Key [1] will acces the value when calling cards_dictionary.
        cards_dictionary = dict(sorted(cards_dictionary.items(), key=lambda item: float(item[1]['marketPrice']) 
                                       if item[1]['marketPrice'] is not None 
                                       else float(item[1]['highPrice'])))
        return cards_dictionary
    
    def create_header_image(self, expansion_path):
        """
        Creates a header image with the expansion logo centered on a background
        
        Args:
            background_path: Path to background image
            expansion_path: Path to expansion logo image
        """
        # Load and resize background to portrait dimensions
        background_img = Image.open(self.background_image)
        background_img = background_img.resize((self.width, self.height), Image.LANCZOS)
        
        # Load expansion image
        expansion_image = Image.open(# The code `expansion_path` is not valid Python syntax. It seems
        # like a placeholder or a comment. It does not perform any
        # specific action or operation in Python.
        expansion_path)
        
        # Calculate sizes to maintain aspect ratio >> Set to 95 % of the total width
        expansion_width = int(self.width * 0.95)
        # Here know the width so calculate the aspect ratio for the height divide the height by width. IF you knew the height would divide the width by the height to know the aspect ratio of it. 
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
        
        # Get current month and year
        current_date = datetime.now()
        date_string = current_date.strftime("%B %Y")
        
        # Create the header text
        header_text = f"Prices {date_string}"
        
        # Calculate text position (centered horizontally, near top vertically)
        text_width = draw.textlength(header_text, font=self.font_type_large)
        x = (self.width - text_width) // 2
        y = 500  # Top margin
        
        # Add text with border effect to the final image
        self.create_text_border(draw, x, y, self.font_type_large, header_text, self.fillcolor, self.shadowcolor_headers)
        
        #Expansion path
        name, _ = os.path.splitext(os.path.basename(expansion_path))
        
        # Save as RGB (removing alpha channel if present)
        self.header_image_path = self.header_image_path.format(name)
        final_img = final_img.convert('RGB')
        final_img.save(self.header_image_path.format(name))
    
    def create_ending_image(self, music_name):
        """
        Create the last image to display after all showing the cards list. 
        """
        music_list = music_name.split('_')
        artist = music_list[0]
        song = ' '.join(i for i in music_list[1:])
        
        name, _ = os.path.splitext(os.path.basename(self.background_image))
        #ToDo: Need to open the image first
        
        bck_img = Image.open(self.background_image).filter(ImageFilter.GaussianBlur(radius=2))
        bck_img = bck_img.resize((self.width, self.height), Image.LANCZOS)
        
        draw = ImageDraw.Draw(bck_img)
        
        lines = ['Music by', f'@{artist}', song]
        
        # Calculate the vertical position for each line
        line_height = self.font_type_large.getbbox('Ay')[3] # Get the bottom pounding box.
        total_height = line_height * len(lines)
        
        # Start position vertical centered
        current_y = (self.height - total_height) // 2
        
        for text in lines:
            
            text_width = self.font_type_large.getbbox(text)[2]
            
            self.create_text_border(draw, (self.width - text_width) // 2, current_y, self.font_type_large, text, self.fillcolor, self.shadowcolor_headers)
            
            current_y += line_height + 70
        
        self.ending_image_path = self.ending_image_path.format(song.replace(' ', '_'), name.replace(' ', '_'))
        
        bck_img = bck_img.convert('RGB')
        bck_img.save(self.ending_image_path)
            
    def process_cards(self, cards_dict):
        """
        Create a picture of each card with the market price on it.

        Args:
            cards_dict (dict): Dictionary of card details
        
        Returns:
            list: List of paths to processed card images
        """
        
        # Load background image and apply blur
        background_img = Image.open(self.background_image)
        blurred_background = background_img.filter(ImageFilter.GaussianBlur(radius=10))
        blurred_background = blurred_background.resize((self.width, self.height), Image.LANCZOS)
                    
        processed_images = []
        
        for i, (name, card) in enumerate(cards_dict.items()):
            # Open the card image >> IN Bytes
            card_img = Image.open(card['imgBytes'])
            # Get the name of the Image
            #name = card['name']
            # Get the count
            card_count = len(cards_dict.keys()) - i
            
            # Resize card image to fit nicely on background
            card_width = int(self.width * 0.75)
            card_height = int(card_width * (card_img.height / card_img.width))
            card_img_resized = card_img.resize((card_width, card_height), Image.LANCZOS)
            
            # Create a new image with blurred background
            final_img = blurred_background.copy()
            
            # Calculate position to center the card
            x_offset = (self.width - card_width) // 2
            y_offset = (self.height - card_height) // 2
            
            # Paste the card onto the background, if there is an alpah value take in account
            if card_img_resized.mode == "RGBA":
                final_img.paste(card_img_resized, (x_offset, y_offset), card_img_resized)
            else:
                final_img.paste(card_img_resized, (x_offset, y_offset))
            # Create a drawing context
            draw = ImageDraw.Draw(final_img)
            
            display_name = f'#{card_count} {name}'
            
            line_height = self.font_type_cards.getbbox('Ay')[3]
            vertical_spacing = int(line_height) * 1.5
            y_base = 100
            
            # Add card name with border
            name_width = draw.textlength(display_name, font=self.font_type_cards)
            
            if name_width > self.width:
                
                words = display_name.split(' ')
                current_line = []
                lines = []
                
                # Create lines smaller then the total width of the image. 
                for word in words:
                    
                    test_line = ' '.join(current_line + [word])
                    test_width = draw.textlength(test_line, self.font_type_cards)
                    
                    if test_width <= self.width:
                        
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        
                        current_line = [word]
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                for i, line in enumerate(lines):
                    
                    name_width = draw.textlength(line, self.font_type_cards)
                    y = y_base + (i * vertical_spacing)
                    
                    self.create_text_border(draw, (self.width - name_width) // 2, y, self.font_type_cards, line, self.fillcolor, self.shadowcolor_cards)
                
            else:
                self.create_text_border(draw, (self.width - name_width) // 2, 220, self.font_type_cards, display_name, self.fillcolor, self.shadowcolor_cards)
            
            # # Add market price
            price = card['marketPrice'] if card['marketPrice'] else card['midPrice']
            price_text = f"Market Price: ${price:.2f}"
            price_width = draw.textlength(price_text, font=self.font_type_cards)
            
            self.create_text_border(draw, (self.width - price_width) // 2,  self.height - 300, self.font_type_cards, price_text, self.fillcolor, self.shadowcolor_cards)
            
            # Save the final image > remove backslashes otherwise incomplete paths. 
            output_path = f'./temp/images/{name.replace('/', '-')}_PRICE_CARD.jpg'
            final_img = final_img.convert('RGB')
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
       
        clips = []
        
        header_clip = ImageClip(self.header_image_path).with_duration(self.clip_duration)
        # header_clip = CrossFadeIn(fade_duration).apply(header_clip)
        header_clip = CrossFadeOut(self.fade_duration).apply(header_clip)
        
        clips.append(header_clip.with_start(0))
        
        current_time = self.clip_duration - self.fade_duration 
        for img_path in processed_images:
            
            # Create base clip with full duration
            clip = ImageClip(img_path).with_duration(self.clip_duration)
            
            # Apply transitions conditionally
            clip = CrossFadeIn(self.fade_duration).apply(clip)
            clip = CrossFadeOut(self.fade_duration).apply(clip)
            
            # Position clip in composition
            clip = clip.with_start(current_time)
            clips.append(clip)
            
            current_time +=  (self.clip_duration - self.fade_duration)

        # Get the songname
        song_path, audio = self.get_music()
        
        song_name, _ = os.path.splitext(os.path.basename(song_path))
        
        # Get the ending Image
        self.create_ending_image(song_name)
        
        # Calculate middle section
        middle_section_duration = 0
        if processed_images:
            middle_section_duration = len(processed_images)*(self.clip_duration-self.fade_duration)
            
        total_duration = middle_section_duration + self.clip_duration
        
        if total_duration < 60:
            ending_clip_duration = 60-total_duration
            ending_clip = ImageClip(self.ending_image_path).with_duration(ending_clip_duration)
            ending_clip = CrossFadeIn(self.fade_duration).apply(ending_clip)
            total_duration = 60
        else:
            ending_clip_duration = self.clip_duration
            ending_clip = ImageClip(self.ending_image_path).with_duration(ending_clip_duration)
            ending_clip = CrossFadeIn(self.fade_duration).apply(ending_clip)
            total_duration += ending_clip_duration
            
        clips.append(ending_clip.with_start(current_time))
        
        # Create final composite with overlapping clips
        final_video = CompositeVideoClip(clips)

        final_video = final_video.with_duration(total_duration)
        
        audio_path = self.get_audio(total_duration, audio, song_name)
        
        final_video = final_video.with_audio(AudioFileClip(audio_path).subclipped(0, total_duration))
        
        # Write the final video
        output_video = f'video/TOP_10_EXPENSIVE_CARDS_{set_name.replace(' ', '_')}.mp4'
        final_video.write_videofile(output_video, fps=24)
        return output_video
    
    def get_music(self):
        music_folder = [s for s in os.listdir('./music/') if s.endswith('.mp4')]
        
        if not music_folder:
            print("No music files found in ./music/ directory")
            return None, None
            
        song_path = os.path.join('./music/', random.choice(music_folder))
        song, _ = os.path.splitext(os.path.basename(song_path))
        
        if song_path.endswith('.mp4'):
            video = VideoFileClip(song_path)
            extracted_audio_path = f'./temp/music/{song}.mp3'
            video.audio.write_audiofile(extracted_audio_path)
            video.close()
            
            # Return the path to the extracted audio, not the audio object
            return extracted_audio_path, AudioFileClip(extracted_audio_path)
        else:
            # If it's already an audio file
            return song_path, AudioFileClip(song_path)
                
        
    def get_audio(self, total_duration, audio, song):
        """
        Find the audio file to add onto the Composite video clip.

        Args:
            total_duraiton (_type_): _description_
        """            
        # Adjust the audio duration
        if audio.duration < total_duration:
            
            repeats = int(total_duration // audio.duration) + 1
            audio_segments = repeats * [audio]
            
            from moviepy import concatenate_audioclips
            looped_audio = concatenate_audioclips(audio_segments)
            adjusted_audio = looped_audio.subclipped(0, total_duration)
        
        else:
            
            adjusted_audio = audio.subclipped(0, total_duration)
        
        # Save the adjusted audio to a temporary file
        adjusted_audio_path = f'./temp/music/{song}_ADJUSTED_AUDIO.mp3'
        adjusted_audio.write_audiofile(adjusted_audio_path)
        return adjusted_audio_path
                
        
    def build_clip(self, expansion_name=None):
        """
        Create a one minute long clip of pokemon cards.
        """
        cards_list = []
        # Load in a set to create the video from
        while not cards_list and len(cards_list) < 10:
            # Get the set_name based on a image.
            expansion_image, set_name = self.get_expansion_name(expansion_name)
            # Retrieve the 
            cards_list = self.query_cards(set_name)
        
        # Close the connection to the DB. 
        self.__close__()
        
        # Background image
        self.background_image = self.get_background_image()
            
        self.create_header_image(expansion_image)
        
        # Download images
        cards_dictionary = self.download_images(cards_list)
        
        # Process cards and get image paths
        processed_images = self.process_cards(cards_dictionary)
        
        output_video = self.create_composite_clip(processed_images, set_name)
        return output_video
        
    def __close__(self):
        """
        Close database connection
        """
        self.conn.close()
        
    def clean_temp_folder(self):
        """
        Clean the folders out of unwanted metadata.
        """
        
        pass