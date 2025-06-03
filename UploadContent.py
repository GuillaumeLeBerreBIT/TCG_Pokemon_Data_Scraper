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


class CallbackHandler(BaseHTTPRequestHandler):
    code = None
    state = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            CallbackHandler.code = params['code'][0]
        if 'state' in params:
            CallbackHandler.state = params['state'][0]

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Authentication successful! You can close this window now.')
        
        # Signal the server to shut down
        threading.Thread(target=self.server.shutdown).start()  

class UploadContentTikTok:
    
    def __init__(self, content):
        
        self.dotenv_file = find_dotenv()
        self.config = dotenv_values(self.dotenv_file)
        self.content = content
        self.headers = {
            'Authorization': f'Bearer {self.config['ACCESS_TOKEN']}',
            'Content-Type': 'application/json; charset=UTF-8'
        }
        
        self.code_verifier = self.create_code_verifier()
        self.code_challenge = self.create_code_challenge(self.code_verifier)
        self.state = secrets.token_urlsafe(16)
        
        
        self.content_path = content
        self.video_size = os.path.getsize(content)
        self.chunk_size = 5542880
        self.total_chunk_count = max(1, self.video_size // self.chunk_size)
        
        self.redirect_uri = 'http://127.0.0.1:5000/callback/'
        self.token_url = 'https://open.tiktokapis.com/v2/oauth/token/'
        self.authorization_url = 'https://www.tiktok.com/v2/auth/authorize/'
        self.refresh_token_url = 'https://open-api.tiktok.com/oauth/refresh_token/'
        
        self.data = None
        
        
    def extract_upload_info(self):
        """
        Do a POST request to catch the Upload URL and the Publish ID from the response 
        """
        
        try: 
            
            url = 'https://open.tiktokapis.com/v2/post/publish/inbox/video/init/'
            payload = {
                "source_info": 
                    {
                    "source": "FILE_UPLOAD",
                    "video_size": self.video_size,  # Replace with actual size as integer
                    "chunk_size": self.video_size if self.total_chunk_count == 1 else self.chunk_size,  # Replace with actual size as integer
                    "total_chunk_count": self.total_chunk_count
                    }
            }
    
            response = requests.post(url=url, json=payload, headers=self.headers)
            
            if response.status_code != 200:
                print("Init error:", response.status_code, response.json())
            
            if response.status_code == 401:
                if self.refresh_access_token():
                    
                    self.headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.post(url=url, json=payload, headers=self.headers)
                
                if response.status_code == 401:
                    token_info = self.fetch_oauth_token()
                    
                    if token_info:
                        self.access_token = token_info['access_token']
                        
                        self.headers['Authorization'] = f'Bearer {self.access_token}'
                        response = requests.post(url=url, json=payload, headers=self.headers)
                    
                    if response.status_code != 200:
                        print(f"Still getting error after new token: {response.status_code} {response.json()}")
                        response.raise_for_status()
                            
            response.raise_for_status()
            
            self.data = response.json()['data']
            return self.data
        
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            raise SystemExit(e)    
        
    def upload_to_tiktok(self):
        """
        Parse the content to TikTok 
        """
        
        with open(self.content_path, 'rb') as f:
            content = f.read()
            
        if self.video_size != len(content):
            
            print("Content sizes aren't identical")
        
        for idx in range(self.total_chunk_count):
            
            chunk_size = self.chunk_size if self.total_chunk_count > 1 else self.video_size
            
            start = idx * chunk_size
            end = (start + chunk_size) -1
            
            if (idx +1) == self.total_chunk_count:
                end = self.video_size-1
        
            headers = {
                'Content-Range': f'bytes {start}-{end}/{self.video_size}',
                'Content-Type': 'video/mp4'
            }
            
            response = requests.put(self.data['upload_url'], headers=headers, data=content)
            response.raise_for_status()
            
        print('Upload succesfull')
            
    def query_creater_info(self):
        """
        """
        
        try:
            url = 'https://open.tiktokapis.com/v2/post/publish/creator_info/query/'
            
            response = requests.post(url, headers=self.headers)
            
            response.raise_for_status
            
            data = response.json()['data']
            
            return data
        
        except requests.exceptions.HTTPError as e:
            
            raise f'{e}'
    
    def direct_post(self):
        
        try:
            url = 'https://open.tiktokapis.com/v2/post/publish/video/init/'
            
            payload = {
                "post_info": 
                {
                    "title": "this will be a funny #cat video on your @tiktok #fyp",
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": True,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": self.video_size,
                    "chunk_size": self.chunk_size if self.total_chunk_count > 1 else self.video_size,
                    "total_chunk_count": self.total_chunk_count
                }
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            data = response.json()['data']
            return data
            
        except requests.exceptions.HTTPError as e:
            raise f'{e}'
    
    def refresh_access_token(self):
        """Use the refresh token to get a new access token without user intervention"""
        refresh_data = {
            'client_key': self.config['CLIENT_KEY'],
            'grant_type': 'refresh_token',
            'refresh_token': self.config['REFRESH_TOKEN']
        }
        try: 
            response = requests.post(self.refresh_token_url, data=refresh_data)
            
            if response.status_code == 200:
                token_info = response.json()['data']
                
                if token_info['access_token'] and token_info['refresh_token'] and token_info['error_code'] == 0:
                    self.access_token = token_info['access_token']
                    self.renew_dotenv_values(token_info=token_info)
                    
                    self.config = dotenv_values(self.dotenv_file)
                    return True
            
            return False
            
        except requests.exceptions.RequestException as e:
            print(f'Refresh token failed: {e}')
            return False
        
    def renew_dotenv_values(self, token_info):
        
        for k, v in token_info.items():
            set_key(self.dotenv_file, k.upper(), str(v))
    
    def create_code_verifier(self, length=64):
        
        allowed_char = string.ascii_letters + string.digits
        return ''.join(secrets.choice(allowed_char) for _ in range(length))
    
    def create_code_challenge(self, code_verifier):
        """
        Create the Code Challenge 

        Args:
            code_verifier (_type_): _description_
        """
        return hashlib.sha256(code_verifier.encode('utf-8')).hexdigest()
    
    def fetch_oauth_token(self):
        """
        Fetch the OAuth 2.0 Token using the proper flow
        """
        # Start local server to handle the callback
        server = HTTPServer(('127.0.0.1', 5000), CallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        # Build authorization URL
        scopes = self.config['SCOPE'].split(',')
        params = {
            'client_key': self.config['CLIENT_KEY'],
            'response_type': 'code',
            'scope': ','.join(scopes),
            'redirect_uri': self.redirect_uri,
            'state': self.state,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256'
        }
        
        # Build the authorization URL
        auth_url = self.authorization_url + '?' + urllib.parse.urlencode(params)
        
        # Open browser for user authorization
        print(f"Opening browser for authorization at: {auth_url}")
        webbrowser.open(auth_url)
        
        # Wait for the callback handler to get the code
        timeout = time.time() + 300  
        while not CallbackHandler.code and time.time() < timeout:
            time.sleep(1)
            
        server.shutdown()
        server.server_close()
        
        # Check if we received the code
        if not CallbackHandler.code:
            raise Exception("Did not receive authorization code")
            
        # Verify state parameter to prevent CSRF
        if CallbackHandler.state != self.state:
            raise Exception("State parameter mismatch")
            
        # Exchange the code for an access token
        token_data = {
            'client_key': self.config['CLIENT_KEY'],
            'client_secret': self.config['CLIENT_SECRET'],
            'code': CallbackHandler.code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code_verifier': self.code_verifier
        }
        
        response = requests.post(self.token_url, data=token_data)
        
        if response.status_code != 200:
            print(f"Token exchange failed: {response.text}")
            raise Exception(f"Failed to get access token: {response.text}")
            
        token_info = response.json()
        self.access_token = token_info['access_token']
        return token_info


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
            
            