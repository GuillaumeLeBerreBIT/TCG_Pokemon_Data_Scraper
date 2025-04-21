from dotenv import dotenv_values, find_dotenv, set_key
import requests
import os
import math
import string
import secrets
import hashlib
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading
import json
import time


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


class UploadContent:
    
    def __init__(self, content):
        
        self.dotenv_file = find_dotenv()
        self.config = dotenv_values(self.dotenv_file)
        self.content = content
        self.headers = {
            'Authorization': f'Bearer {self.config['ACCESS_TOKEN']}',
            'Content-Type': 'application/json'
        }
        
        self.code_verifier = self.create_code_verifier()
        self.code_challenge = self.create_code_challenge(self.code_verifier)
        self.state = secrets.token_urlsafe(16)
        
        self.videosize = os.path.getsize(self.content)
        self.chunck_size = 5 * 1024 * 1024
        self.total_chunk_count = math.ceil(self.videosize / self.chunck_size)
        
        self.redirect_uri = 'http://127.0.0.1:5000/callback/'
        self.token_url = 'https://open.tiktokapis.com/v2/oauth/token/'
        self.authorization_url = 'https://www.tiktok.com/v2/auth/authorize/'
        self.refresh_token_url = 'https://open-api.tiktok.com/oauth/refresh_token/'
        
        
    def extract_upload_info(self):
        """
        Do a POST request to catch the Upload URL and the Publish ID from the response 
        """
        
        try: 
            
            url = 'https://open.tiktokapis.com/v2/post/publish/inbox/video/init/'
            data = {
                "source": "FILE_UPLOAD",
                "video_size": self.videosize,  # Replace with actual size as integer
                "chunk_size": self.videosize,  # Replace with actual size as integer
                "total_chunk_count": 1
            }
            
            response = requests.post(url=url, json=data, headers=self.headers)
            
            if response.status_code == 401:
                self.refresh_access_token()
                            
            response.raise_for_status()
            
            data = response.json()['data']
            
            return data
        
        except requests.exceptions.HTTPError as e:
            
            raise SystemExit(e)    
    
    def upload_to_tiktok(self, url):
        """
        Parse the content to TikTok 
        """
        headers = {
            'Content-Range': 'bytes 0-30567099/30567100',
            'Content-Type': 'video/mp4'
        }
        
        requests.put(url, headers=headers, data=self.content)
        
    
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
                    
                return token_info
            
        except requests.exceptions.RequestException as e:
            # If refresh fails, we need to do the full auth flow again >> This will to be manually accepted. 
            raise f'Need to request a new OAtuh Access Token. The following Request Exception occured: {e}'
        
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

