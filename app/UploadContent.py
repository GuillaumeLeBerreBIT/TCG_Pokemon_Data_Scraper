from dotenv import dotenv_values, find_dotenv, set_key
import requests
import os
import math
import string
import secrets
import hashlib
import webbrowser
import urllib.parse
import threading
import json
import time
import httplib2
import textwrap
import pickle
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from auth.google_auth import GoogleAuth

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError


class UploadContentYouTube:
    
    def __init__(self, video_path='', set_expansion='', artist_song='', card_count=15):

        self.video_path = video_path
        self.artist_song = artist_song
        self.set_expansion = set_expansion
        self.card_count = card_count
        
        self.UPLOAD_SCOPE = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ]
        self.API_SERVICE_NAME = "youtube"   
        self.API_VERSION = "v3"
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.CLIENTS_SECRETS_FILE = os.path.join(BASE_DIR, 'token', 'client_secret.json')
        self.TOKEN_PICKLE_FILE = os.path.join(BASE_DIR, 'token', 'token.youtube.pickle')
        
        self.CREDENTIALS = GoogleAuth.get_credentials(self.TOKEN_PICKLE_FILE, self.UPLOAD_SCOPE,
                                                      instance='YOUTUBE')
        
        self.tags = [
            'pokemon', 'pokemontcg', 'pokemoncards', 'tcg', 'top10',
            'pokemonshorts', 'pokemoncollector', 'pokemoncommunity',
            'rarepokemon', 'cardprices', 'pokemonmarket', 'pokemonpulls',
            'tcgcommunity', 'pokemonpack', 'secretrare',
        ]
    
    def split_artist_song(self, artist_song):
        
        splitted_artist = artist_song.split('_', 1)
        
        if len(splitted_artist) < 2:
            return splitted_artist[0], splitted_artist[0].replace('_', ' ')
        else:
            return splitted_artist[0], splitted_artist[1].replace('_', ' ')
    
    def split_expansion_full_name(self, expansion_full_name):
        
        if '-' in expansion_full_name:
            set_name, expansion_name = tuple(expansion_full_name.split('-'))
        else:
            expansion_name = expansion_full_name
            set_name = None
            
        return set_name, expansion_name
            
    
    def authenticate_youtube(self):
        
        return build(self.API_SERVICE_NAME, self.API_VERSION, credentials=self.CREDENTIALS)
    
    def initialize_upload(self, youtube):
        
        artist, song = self.split_artist_song(self.artist_song)
        set_name , expansion_name = self.split_expansion_full_name(self.set_expansion)
        
        body=dict(
            snippet=dict(
                title=f'Top {self.card_count} Most Expensive {self.set_expansion} Cards ({datetime.strftime(datetime.now(), "%B %Y")}) #pokemon #tcg #shorts',
                description=textwrap.dedent(f"""
                Which card from {self.set_expansion} is worth the most right now? Here are the Top {self.card_count} Most Expensive Cards ranked by market price! 💎

                Do you own any of these? Let me know in the comments! 👇

                🎵 Music: {song} by {artist}

                ━━━━━━━━━━━━━━━━━━━━━━
                🔔 Subscribe for weekly Pokemon TCG price updates!
                ━━━━━━━━━━━━━━━━━━━━━━

                #pokemon #pokemontcg #pokemoncards #{expansion_name.strip().replace(' ', '')} #{set_name.strip().replace(' ', '').replace('&', '') if set_name else 'pokemoncards'} #pokemonshorts #tcgcommunity #pokemoncollector #pokemonpulls #rarepokemon #top10 #cardprices #pokemonmarket
                """),
                tags=self.tags,
                categoryId="22"
            ),
            status=dict(
                privacyStatus='public',
                madeForKids=False
            )
        )
        
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(self.video_path, chunksize=-1)
        )
        
        response = request.execute()
        return response
    
    def upload_to_yt(self):
        
        youtube = self.authenticate_youtube()
        try:
            result = self.initialize_upload(youtube)
            print('Upload succesfully completed.')
            return result
        except Exception as e:
            
            raise f'An HTTP error {e} occurred: {e}' 
        
    def list_channels(self):
        youtube = self.authenticate_youtube()
        
        channels = youtube.channels().list(part="snippet", mine=True).execute()
        for c in channels.get('items', []):
            print(c['id'], c['snippet']['title'])
            

if __name__ == '__main__':
    
    upload_content = UploadContentYouTube()
    upload_content.list_channels()
    