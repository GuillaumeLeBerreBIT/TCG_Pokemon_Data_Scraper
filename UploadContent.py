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

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError


class UploadContentYouTube:
    
    def __init__(self, video_path, set_expansion, artist_song):
        
        self.video_path = video_path
        self.artist_song = artist_song
        self.set_expansion = set_expansion
        
        self.UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
        self.API_SERVICE_NAME = "youtube"   
        self.API_VERSION = "v3"
        self.CLIENTS_SECRETS_FILE = './token/client_secret.json'
        self.TOKEN_PICKLE_FILE = './token/token.pickle'
        
        self.tags = ['pokemon', 'tcg', 'top10']
    
    def split_artist_song(self, artist_song):
        
        splitted_artist = artist_song.split('_', 1)
        return splitted_artist[0], splitted_artist[1].replace('_', ' ')
    
    def split_expansion_full_name(self, expansion_full_name):
        
        if '-' in expansion_full_name:
            set_name, expansion_name = tuple(expansion_full_name.split('-'))
        else:
            expansion_name = expansion_full_name
            set_name = None
            
        return set_name, expansion_name
            
    
    def authenticate_youtube(self):
        credentials = None
        
        if os.path.exists(self.TOKEN_PICKLE_FILE):
            try:
                with open(self.TOKEN_PICKLE_FILE, 'rb') as token:
                    credentials = pickle.load(token)
            except (pickle.UnpicklingError, EOFError, FileNotFoundError) as e:
                print(f'Failed to load credentials: {e}')
        
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except RefreshError as e:
                    credentials = None
                    
            # If not valid run local server flow.
            if not credentials or not credentials.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CLIENTS_SECRETS_FILE, self.UPLOAD_SCOPE)
                credentials = flow.run_local_server(port=8080)
        
            # Save the credentials for the next run
            try:
                with open(self.TOKEN_PICKLE_FILE, 'wb') as token:
                    pickle.dump(credentials, token)
            except Exception as e:
                print('Failed to save credentials: {e}')
        
        return build(self.API_SERVICE_NAME, self.API_VERSION, credentials=credentials)
    
    def initialize_upload(self, youtube):
        
        artist, song = self.split_artist_song(self.artist_song)
        set_name , expansion_name = self.split_expansion_full_name(self.set_expansion)
        
        body=dict(
            snippet=dict(
                title=f'TOP 10 EXPENSIVE CARDS {self.set_expansion} - {datetime.strftime(datetime.now(), "%B %Y")} #pokemon #tcg #top10',
                description=textwrap.dedent(f"""
                Here are the Top 10 Most Expensive Cards from the {self.set_expansion}! 💎✨
                Watch to see which stunning alt-arts and secret rares top the list!
                
                🎵 Music by: {artist}
                🎶 Track: {song}
                #pokemon  #pokemontcg  #pokemoncards  #pokemoncommunity  #tcgcommunity  #pokemoncollector  
                #{set_name.strip().replace(' ', '').replace('&', '') if set_name else 'pokemoncollectors'} #{expansion_name.strip().replace(' ','')}
                #pokemonpulls  #rarepokemon #top10 #lofi #lofibeats  #lofimusic  #chillvibes
                """),
                tags=self.tags,
                categoryId="22"
            ),
            status=dict(
                privacyStatus='public'
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
            print('Download succesfully completed.')
            return result
        except Exception as e:
            
            raise f'An HTTP error {e} occurred: {e}' 
            
            