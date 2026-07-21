import sqlite3
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import os
import shutil
import random
from thefuzz import process
from moviepy import ImageClip
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from moviepy.video.compositing import CompositeVideoClip
from moviepy import *
from datetime import datetime
from dotenv import load_dotenv
from auth.google_auth import GoogleAuth

import cv2
import numpy as np

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# import torch
# from basicsr.archs.rrdbnet_arch import RRDBNet
# from basicsr.utils.download_util import load_file_from_url
# from realesrgan import RealESRGANer
# from realesrgan.archs.srvgg_arch import SRVGGNetCompact


class VideoCreation:
    
    def __init__(self, expansion, expansion_image_path, cards_dict={}):
        """
        Initialize the video creation process
        """
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_dotenv(os.path.join(self.BASE_DIR, '.env'))
        self.SCOPES = [
            "https://www.googleapis.com/auth/drive"
        ]
        self.TOKEN_PICKLE_FILE = os.path.join(self.BASE_DIR, 'token', 'token.drive.pickle')
        self.CREDENTIALS = GoogleAuth.get_credentials(self.TOKEN_PICKLE_FILE, self.SCOPES, instance='DRIVE')

        self.expansion_images_dir = os.path.join(self.BASE_DIR, 'images')
        self.temp_folder = os.path.join(self.BASE_DIR, 'temp')

        self.expansion = expansion
        self.cards_dict = cards_dict
        self.expansion_image_path = expansion_image_path

        self.expansion_full_name = expansion if expansion else None

        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }

        # Ensure output directories exist
        os.makedirs(os.path.join(self.BASE_DIR, 'temp', 'images'), exist_ok=True)
        os.makedirs(os.path.join(self.BASE_DIR, 'temp', 'music'), exist_ok=True)
        os.makedirs(os.path.join(self.BASE_DIR, 'video'), exist_ok=True)

        #Portrait sizes
        self.width = 1080
        self.height = 1980

        self.background_image = None
        self.header_image_path = os.path.join(self.BASE_DIR, 'temp', 'images', '{}_EXPANSION_IMAGE.jpg')
        self.ending_image_path = os.path.join(self.BASE_DIR, 'temp', 'images', '{}_{}_ENDING.jpg')
        self.hook_image_path = os.path.join(self.BASE_DIR, 'temp', 'images', '{}_HOOK.jpg')

        try:
            # Load a font type specific to Pokemon styled theme
            self.font_type_large = ImageFont.truetype(os.path.join(self.BASE_DIR, 'font', 'Bangers-Regular.ttf'), 150)
            self.font_type_cards = ImageFont.truetype(os.path.join(self.BASE_DIR, 'font', 'Bangers-Regular.ttf'), 120)
            self.font_type_price = ImageFont.truetype(os.path.join(self.BASE_DIR, 'font', 'Bangers-Regular.ttf'), 90)
        except IOError:
            self.font_type_large = ImageFont.load_default(size=150)
            self.font_type_cards = ImageFont.load_default(size=120)
            self.font_type_price = ImageFont.load_default(size=90)
        
        self.fillcolor = (255, 255, 255)
        self.shadowcolor_headers = 'black'
        self.shadowcolor_cards = (255, 205, 30)
        
         # Define duration parameters
        self.clip_duration = 2.5  # Fallback per-card duration; the real value is computed per video from the card count
        self.fade_duration = 0.5  # Seconds for fade effects
        self.hook_duration = 2  # Seconds the opening hook clip stays
        self.header_duration = 2.5  # Seconds the expansion-logo header stays
        self.ending_duration = 3.5  # Target seconds for the closing credits clip
        self.min_card_duration = 2.0  # Fastest pace allowed per card
        self.max_card_duration = 4.0  # Slowest pace allowed per card
        self.target_video_duration = 60  # Seconds the whole short aims to fill
        
        self._realesrgan_model = None
        self._realesrgan_model_name = None
        
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
            
        self.expansion_full_name = os.path.splitext(expansion_image)[0].replace('_', ' ')
        
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
        
        backgrounds_dir = os.path.join(self.BASE_DIR, 'backgrounds')
        images = [f for f in os.listdir(backgrounds_dir) if f.endswith(('.jpg', '.png'))]

        return os.path.join(backgrounds_dir, random.choice(images))
        
                
    def query_cards(self, set_name):
        """
        Query the database for the top 10 most expensive cards for a Set.

        Args:
            set_name (str): Name of the Pokémon card set
        
        Returns:
            list: List of card details
        """
        rows = []
        if '-' in self.expansion_full_name:
            expansion_name, set_name = tuple(self.expansion_full_name.split('-'))
        
            try:
                like_pattern_exp = f'%{expansion_name}%'
                like_pattern_set = f'%{set_name}%'
                self.cursor.execute("""
                    SELECT name, imageUrl, lowPrice, midPrice, highPrice, marketPrice
                    FROM pokemon 
                    WHERE setName LIKE ? AND setName LIKE ?
                    AND extNumber IS NOT '' 
                    AND extCardType IS NOT ''
                    AND (marketPrice IS NOT '' OR midPrice IS NOT '')
                    ORDER BY CAST(COALESCE(marketPrice, '0') AS REAL) DESC, 
                        CAST(COALESCE(midPrice, '0') AS REAL) DESC
                    LIMIT 10
                """, (like_pattern_exp, like_pattern_set,)
                )
                rows = self.cursor.fetchall()
            except sqlite3.IntegrityError as e:
                print(f"Couldn't query the databse: {e}")
        
        if not rows:
            try:
                like_pattern = f'{set_name}%'
                self.cursor.execute("""
                    SELECT name, imageUrl, lowPrice, midPrice, highPrice, marketPrice
                    FROM pokemon 
                    WHERE setName LIKE ?
                    AND extNumber IS NOT '' 
                    AND extCardType IS NOT ''
                    AND (marketPrice IS NOT '' OR midPrice IS NOT '')
                    ORDER BY CAST(COALESCE(marketPrice, '0') AS REAL) DESC, 
                        CAST(COALESCE(midPrice, '0') AS REAL) DESC
                    LIMIT 10
                """, (like_pattern,)
                )
                rows = self.cursor.fetchall()
            except sqlite3.IntegrityError as e:
                print(f"Couldn't query the databse: {e}")
        
        if not rows:
            try:
                like_pattern = f'%{set_name}%'
                self.cursor.execute("""
                    SELECT name, imageUrl, lowPrice, midPrice, highPrice, marketPrice
                    FROM pokemon 
                    WHERE setName LIKE ? 
                    AND extNumber IS NOT '' 
                    AND extCardType IS NOT ''
                    AND (marketPrice IS NOT '' OR midPrice IS NOT '')
                    ORDER BY CAST(COALESCE(marketPrice, '0') AS REAL) DESC, 
                        CAST(COALESCE(midPrice, '0') AS REAL) DESC
                    LIMIT 10
                """, (like_pattern,)
                )
                rows = self.cursor.fetchall()
            except sqlite3.IntegrityError as e:
                print(f"Couldn't query the databse: {e}")
        
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
            image_url_1000 = imageUrl.replace('_200w', '_in_1000x1000')
            
            try:
                response = requests.get(url=image_url_1000, headers=self.headers)
                image_downloaded_url = image_url_1000
                response.raise_for_status()
                
            except requests.exceptions.HTTPError as e:
                
                print("Couldn't retrieve the image from increased size: {e}")
           
                response = requests.get(url=imageUrl, headers=self.headers)
                image_downloaded_url = imageUrl
            
            if response.status_code == 200:
                # Here already in Bytes can direclty save it to BytesIO
                img_bytes = BytesIO(response.content)
                
                # price = marketPrice if marketPrice else midPrice
                cards_dictionary[name] = {
                    'imageUrl': image_downloaded_url,
                    'lowPrice': lowPrice,
                    'midPrice': midPrice,
                    'highPrice': highPrice,
                    'marketPrice': marketPrice,
                    'imgBytes': img_bytes
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
        final_img.save(self.header_image_path)
    
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
            
            bbox = self.font_type_large.getbbox(text)
            text_width = bbox[2] - bbox[0]
            
            self.create_text_border(draw, (self.width - text_width) // 2, current_y, self.font_type_large, text, self.fillcolor, self.shadowcolor_headers)
            
            current_y += line_height + 70
        
        self.ending_image_path = self.ending_image_path.format(song.replace(' ', '_'), name.replace(' ', '_'))

        bck_img = bck_img.convert('RGB')
        bck_img.save(self.ending_image_path)

    def create_hook_image(self, cards_dict):
        """
        Create the opening hook image teasing the #1 most expensive card's price.
        """
        top_name, top_card = list(cards_dict.items())[-1]
        price = top_card.get('marketPrice') or top_card.get('midPrice')

        bck_img = Image.open(self.background_image).filter(ImageFilter.GaussianBlur(radius=10))
        bck_img = bck_img.resize((self.width, self.height), Image.LANCZOS)

        card_img = Image.open(top_card.get('imgPath') or top_card.get('imgBytes'))
        card_width = int(self.width * 0.65)
        card_height = int(card_width * (card_img.height / card_img.width))
        resized_card = card_img.resize((card_width, card_height), Image.LANCZOS)

        x_offset = (self.width - card_width) // 2
        y_offset = (self.height - card_height) // 2

        if resized_card.mode == "RGBA":
            bck_img.paste(resized_card, (x_offset, y_offset), resized_card)
        else:
            bck_img.paste(resized_card, (x_offset, y_offset))

        draw = ImageDraw.Draw(bck_img)

        top_text = "This card is worth"
        price_text = f"${float(price):.2f}!?"

        top_width = draw.textlength(top_text, font=self.font_type_cards)
        self.create_text_border(draw, (self.width - top_width) // 2, y_offset - 220, self.font_type_cards, top_text, self.fillcolor, self.shadowcolor_headers)

        price_width = draw.textlength(price_text, font=self.font_type_large)
        price_x = int((self.width - price_width) // 2)
        price_y = y_offset + card_height + 40

        price_bbox = self.font_type_large.getbbox('Ay$0.9!?')
        price_height = price_bbox[3] - price_bbox[1]

        # Solid plate behind the price so it stays clearly visible after the glitch
        plate_pad_x, plate_pad_y = 40, 24
        glitch_box = (
            int(max(price_x - plate_pad_x, 0)),
            int(max(price_y - plate_pad_y, 0)),
            int(min(price_x + int(price_width) + plate_pad_x, self.width)),
            int(min(price_y + price_height + plate_pad_y, self.height)),
        )
        draw.rounded_rectangle(glitch_box, radius=24, fill=(12, 12, 18))
        self.create_text_border(draw, price_x, price_y, self.font_type_large, price_text, self.fillcolor, self.shadowcolor_headers)

        # Glitch out the exact amount: pixelate the price into blocks so viewers see
        # a price is there but can't read it. The countdown reveals it later.
        region = bck_img.crop(glitch_box)
        block = 40
        small = (max(1, region.width // block), max(1, region.height // block))
        region = region.resize(small, Image.BILINEAR).resize(region.size, Image.NEAREST)
        region = region.filter(ImageFilter.GaussianBlur(radius=3))
        bck_img.paste(region, glitch_box)

        self.hook_image_path = self.hook_image_path.format(top_name.replace('/', '-').replace(' ', '_'))
        bck_img = bck_img.convert('RGB')
        bck_img.save(self.hook_image_path)

    def compute_card_clip_duration(self, card_count):
        """
        Spread the leftover time from the fixed target duration across the cards,
        instead of always using a fixed per-card duration and dumping the slack
        into the closing credits clip.
        """
        if card_count <= 0:
            return self.clip_duration

        fixed_intro = (self.hook_duration - self.fade_duration) + (self.header_duration - self.fade_duration)
        available_for_cards = self.target_video_duration - self.ending_duration - self.fade_duration - fixed_intro
        duration = self.fade_duration + available_for_cards / card_count

        return max(self.min_card_duration, min(self.max_card_duration, duration))

    def apply_circle_reveal(self, clip, dist_from_center, max_radius):
        """
        Reveal the clip through a circle that expands from the centre of the frame over
        fade_duration, so the next card appears to "open up" on top of the previous one.

        Args:
            clip: the incoming card clip
            dist_from_center: precomputed HxW array of each pixel's distance to the centre
            max_radius: radius (px) at which the circle fully covers the frame
        """
        reveal = self.fade_duration
        feather = 6.0  # soft anti-aliased edge on the circle

        def mask_frame(t):
            progress = min(t / reveal, 1.0) if reveal else 1.0
            r = progress * max_radius
            return np.clip((r - dist_from_center) / feather + 0.5, 0.0, 1.0)

        mask_clip = VideoClip(mask_frame, is_mask=True, duration=clip.duration)
        return clip.with_mask(mask_clip)

    def enhance_card_image_traditional(self, image, card_width, card_height, quality='balanced'):
        
        cv_img = np.array(image.convert('RGB'))
        cv_img = cv_img[:, :, ::-1].copy()
        
        cv_img_resized = cv2.resize(cv_img, (card_width, card_height), interpolation=cv2.INTER_CUBIC)
        # Convert to PIL Image
        card_img_resized = Image.fromarray(cv_img_resized[:, :, ::-1])
        
        enhancer = ImageEnhance.Sharpness(card_img_resized)
        sharpened_image = enhancer.enhance(1.5)
            
        return sharpened_image
    
    def ehance_card_image_advanced(self, image, card_width, card_height, quality='balanced'):
        try:
            #Image enhancing protocol.
            img_array = np.array(image)
            
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            if quality == 'fast':
                model_name = 'realesr-animevideov3'
                
            elif quality == 'balanced': 
                model_name = 'realesr-general-x4v3'
                
            else:
                model_name = 'RealESRGAN_x4plus_anime_6B'
            
            
            if not hasattr(self, '_realesrgan_model') or self._realesrgan_model_name != model_name:
                
                if model_name == 'realesr-general-x4v3':
                    model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4, act_type='prelu')
                    netscale = 4
                    file_url = [
                        'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth',
                        'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth'
                    ]
                    
                elif model_name == 'realesr-animevideov3':
                    model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=16, upscale=4, act_type='prelu')
                    netscale = 4
                    file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth']
                    
                else:    # 'RealESRGAN_x4plus_anime_6B'
                    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
                    netscale = 4
                    file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth']
                    
                weights_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights')
                model_path = os.path.join(weights_path, f'{model_name}.pth')
                
                if not os.path.isfile(model_path):
                    for url in file_url:
                        model_path = load_file_from_url(url=url, model_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights'),
                                                        progress=True, file_name=None)
                
                self._realesrgan_model = RealESRGANer(
                            scale=netscale,
                            model_path=model_path,
                            dni_weight=None,
                            model=model,
                            tile=400,
                            tile_pad=10,
                            pre_pad=0,
                            half=device=='cuda',
                            device=device
                            )
                
                self._realesrgan_model_name = model_name
                
            height, width = img_array.shape[:2]
            very_small = max(width, height) < 150
            if very_small:
                
                image = image.resize((width*2, height*2), Image.LANCZOS)
                img_array = np.array(image)
                        
                        
            
        except (ImportError, Exception) as e:
            print(f'Advanced super resolution is not available: {e}')
            self.enhance_card_image_traditional(image, card_width, card_height)
    
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
            card_img = Image.open(card.get('imgPath') or  card.get('imgBytes'))
            # Get the name of the Image
            #name = card['name']
            # Get the count
            card_count = len(cards_dict.keys()) - i
            
            # Resize card image to fit nicely on background, leaving headroom above
            # for the name plate and price badge
            card_width = int(self.width * 0.75)
            card_height = int(card_width * (card_img.height / card_img.width))
            resized_image = card_img.resize((card_width, card_height), Image.LANCZOS)
            
            # sharpened_image = self.enhance_card_image(card_img, card_width, card_height)
            
            # Create a new image with blurred background
            final_img = blurred_background.copy()
            
            # Calculate position to center the card
            x_offset = (self.width - card_width) // 2
            y_offset = (self.height - card_height) // 2
            
            # Paste the card onto the background, if there is an alpah value take in account
            if resized_image.mode == "RGBA":
                final_img.paste(resized_image, (x_offset, y_offset), resized_image)
            else:
                final_img.paste(resized_image, (x_offset, y_offset))
            # Create a drawing context
            draw = ImageDraw.Draw(final_img)
            
            display_name = f'#{card_count} {name}'

            line_height = self.font_type_cards.getbbox('Ay')[3]
            line_spacing = int(line_height * 1.3)
            name_top = 50
            max_text_width = self.width - 100

            # Wrap the rank + name into lines that fit within the frame
            words = display_name.split(' ')
            lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                test_width = draw.textlength(test_line, font=self.font_type_cards)

                if test_width <= max_text_width or not current_line:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))

            line_widths = [draw.textlength(line, font=self.font_type_cards) for line in lines]
            block_width = max(line_widths)
            block_height = line_spacing * (len(lines) - 1) + line_height

            # Clean dark name plate behind the rank + card name for legibility
            plate_pad_x, plate_pad_y = 50, 26
            plate_x0 = (self.width - block_width) // 2 - plate_pad_x
            plate_x1 = (self.width + block_width) // 2 + plate_pad_x
            plate_y0 = name_top - plate_pad_y
            plate_y1 = name_top + block_height + plate_pad_y

            draw.rounded_rectangle((plate_x0, plate_y0, plate_x1, plate_y1), radius=28, fill=(12, 12, 18))
            draw.rounded_rectangle((plate_x0, plate_y0, plate_x1, plate_y1), radius=28, outline=self.shadowcolor_cards, width=4)

            for i, line in enumerate(lines):
                line_y = name_top + (i * line_spacing)
                self.create_text_border(draw, (self.width - line_widths[i]) // 2, line_y, self.font_type_cards, line, self.fillcolor, self.shadowcolor_cards)

            # Add market price as a badge that sits just above the card, below the name plate
            price = card.get('marketPrice') or card.get('midPrice')
            price_text = f"${float(price):.2f}"
            price_bbox = draw.textbbox((0, 0), price_text, font=self.font_type_price)
            price_text_width = price_bbox[2] - price_bbox[0]
            price_text_height = price_bbox[3] - price_bbox[1]

            badge_pad_x, badge_pad_y = 28, 16
            badge_width = price_text_width + badge_pad_x * 2
            badge_height = price_text_height + badge_pad_y * 2
            badge_gap = 24

            badge_margin_right = 40
            badge_x1 = x_offset + card_width - badge_margin_right
            badge_x0 = badge_x1 - badge_width
            badge_y0 = plate_y1 + badge_gap
            badge_y1 = badge_y0 + badge_height

            # Keep the badge from dipping onto the card art if the name wrapped to extra
            # lines, but never push it back up into the name plate to do so
            max_badge_y1 = y_offset - 16
            if badge_y1 > max_badge_y1 and max_badge_y1 - badge_height >= plate_y1 + badge_gap:
                badge_y1 = max_badge_y1
                badge_y0 = badge_y1 - badge_height

            draw.rounded_rectangle((badge_x0, badge_y0, badge_x1, badge_y1), radius=18, fill=(255, 205, 30))
            draw.rounded_rectangle((badge_x0, badge_y0, badge_x1, badge_y1), radius=18, outline='black', width=4)

            price_x = badge_x0 + badge_pad_x - price_bbox[0]
            price_y = badge_y0 + badge_pad_y - price_bbox[1]
            draw.text((price_x, price_y), price_text, font=self.font_type_price, fill='black')
            
            # Save the final image > remove backslashes otherwise incomplete paths. 
            output_path = os.path.join(self.BASE_DIR, 'temp', 'images', f"{name.replace('/', '-')}_PRICE_CARD.png")
            final_img = final_img.convert('RGB')
            final_img.save(output_path, format='PNG')
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

        # Spread any slack time across the cards instead of padding the ending clip
        card_clip_duration = self.compute_card_clip_duration(len(processed_images))

        # Hook clip: teases the #1 card's price before the countdown starts
        hook_clip = ImageClip(self.hook_image_path).with_duration(self.hook_duration)
        hook_clip = CrossFadeOut(self.fade_duration).apply(hook_clip)

        clips.append(hook_clip.with_start(0))

        current_time = self.hook_duration - self.fade_duration

        header_clip = ImageClip(self.header_image_path).with_duration(self.header_duration)
        header_clip = CrossFadeIn(self.fade_duration).apply(header_clip)
        # No fade-out: the first card's circle reveal opens up on top of the header

        clips.append(header_clip.with_start(current_time))

        # Precompute each pixel's distance to the frame centre once; only the radius
        # changes over time in the circle-reveal mask
        Y, X = np.ogrid[:self.height, :self.width]
        dist_from_center = np.sqrt((X - self.width / 2) ** 2 + (Y - self.height / 2) ** 2)
        max_radius = float(np.sqrt((self.width / 2) ** 2 + (self.height / 2) ** 2)) + 6.0

        current_time += self.header_duration - self.fade_duration
        for i, img_path in enumerate(processed_images):

            # Create base clip with full duration
            clip = ImageClip(img_path).with_duration(card_clip_duration)

            # Reveal each card through an expanding circle over the previous one
            clip = self.apply_circle_reveal(clip, dist_from_center, max_radius)

            # Position clip in composition
            clip = clip.with_start(current_time)
            clips.append(clip)

            current_time +=  (card_clip_duration - self.fade_duration)

        # Get the songname
        song_path, audio = self.get_music()

        song_name, _ = os.path.splitext(os.path.basename(song_path))

        # Get the ending Image
        self.create_ending_image(song_name)

        # The last non-ending clip keeps fading out for fade_duration past its start time
        total_duration = current_time + self.fade_duration

        if total_duration < self.target_video_duration:
            ending_clip_duration = self.target_video_duration - total_duration
            ending_clip = ImageClip(self.ending_image_path).with_duration(ending_clip_duration)
            ending_clip = CrossFadeIn(self.fade_duration).apply(ending_clip)
            total_duration = self.target_video_duration
        else:
            ending_clip_duration = self.ending_duration
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
        card_count = len(processed_images)
        output_video = os.path.join(self.BASE_DIR, 'video', f"TOP_{card_count}_EXPENSIVE_CARDS_{set_name.replace(' ', '_')}_{datetime.strftime(datetime.now(), '%m%d%Y%H%M')}.mp4")
        final_video.write_videofile(output_video, fps=24)
        return output_video, song_name, card_count
    
    def get_music(self):
        
        song_path, song = self.retrieve_audio_file()
                
        if song_path.endswith('.mp4'):
            video = VideoFileClip(song_path)
            os.makedirs(os.path.join(self.BASE_DIR, 'temp', 'music'), exist_ok=True)
            extracted_audio_path = os.path.join(self.BASE_DIR, 'temp', 'music', f'{song}.mp3')
            video.audio.write_audiofile(extracted_audio_path)
            video.close()
            
            # Return the path to the extracted audio, not the audio object
            return extracted_audio_path, AudioFileClip(extracted_audio_path)
        else:
            # If it's already an audio file
            return song_path, AudioFileClip(song_path)
                
    def retrieve_audio_file(self):
        
        service = build('drive', 'v3', credentials=self.CREDENTIALS)
        
        results = service.files().list(
            q=f"'{os.getenv('GOOGLE_DRIVE_ID')}' in parents",
            fields='files(id, name, mimeType)'
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            raise FileNotFoundError('No files could be found on the Google Drive')
        try:
            f = random.choice(files)
            
            request = service.files().get_media(fileId= f.get('id'))
            
            song = BytesIO()
            
            downloader = MediaIoBaseDownload(song, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
        except HttpError as e:
            print(f"An error occurred: {e}")
            file = None
            
        save_path = os.path.join(self.BASE_DIR, 'music', f.get('name', ''))

        try:
            os.makedirs(os.path.join(self.BASE_DIR, 'music'), exist_ok=True)
            with open(save_path, 'wb') as out:
                out.write(song.getvalue())
        except Exception as e:
            raise e

        return save_path, os.path.splitext(f.get('name', ''))[0]
    
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
        adjusted_audio_path = os.path.join(self.BASE_DIR, 'temp', 'music', f'{song}_ADJUSTED_AUDIO.mp3')
        adjusted_audio.write_audiofile(adjusted_audio_path)
        return adjusted_audio_path
                
        
    def build_clip(self):
        """
        Create a one minute long clip of pokemon cards.
        """
        # Background image
        self.background_image = self.get_background_image()

        self.create_header_image(self.expansion_image_path)
        self.create_hook_image(self.cards_dict)

        # Process cards and get image paths
        processed_images = self.process_cards(self.cards_dict)

        output_video, song_name, card_count = self.create_composite_clip(processed_images, self.expansion)

        self.clean_temp_folder()

        return output_video, self.expansion_full_name, song_name, card_count
        
    def __close__(self):
        """
        Close database connection
        """
        self.conn.close()
        
    def clean_temp_folder(self):
        """
        Clean the folders out of unwanted metadata.
        """
        
        temp_dir = os.path.join(self.BASE_DIR, 'temp')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

        for folder in ['music', 'images']:
            folder_path = os.path.join(self.BASE_DIR, folder)
            if os.path.exists(folder_path):
                for f in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, f)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            
    
    
if __name__ == "__main__":
    
    video_creation = VideoCreation('', '', {f'card_{i}': i for i in range(11)})
    video_creation.retrieve_audio_files()