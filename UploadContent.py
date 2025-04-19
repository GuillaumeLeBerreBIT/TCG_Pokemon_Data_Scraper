from dotenv import dotenv_values
from oauthlib.oauth2 import WebApplicationClient
from rauth import OAuth2Service
import requests
import os 
import math
import string
import secrets
import hashlib


class UploadContent:
    
    def __init__(self, content):
        
        self.config = dotenv_values('.env')
        self.content = content
        self.headers = {
            'Authorization': f'Bearer {self.config['ACCESS_TOKEN']}',
            'Content-Type': 'application/json'
        }
        
        self.code_verifier = self.create_code_verifier()
        self.code_challenge = self.create_code_challenge(self.code_verifier)
        
        self.videosize = os.path.getsize(self.content)
        self.chunck_size = 5 * 1024 * 1024
        self.total_chunk_count = math.ceil(self.videosize / self.chunck_size)
        
        self.redirect_uri = 'http://127.0.0.1:5000/callback/'
        self.token_url = 'https://open.tiktokapis.com/v2/oauth/token/'
        self.authorization_url = 'https://www.tiktok.com/v2/auth/authorize/'
        
        
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
                self.fetch_o_auth()
            
            response.raise_for_status()
            
            
            return response
        
        except requests.exceptions.HTTPError as e:
            
            raise SystemExit(e)
            
    def fetch_o_auth(self):
        """
        Fetch the OAuth 2.0 Token
        """
        scopes = self.config['SCOPE'].split(',')
        
        service = OAuth2Service(
            name='tiktok',
            authorize_url=self.authorization_url,
            access_token_url=self.token_url,
            base_url='https://open.tiktokapis.com/v2/',
            client_id=self.config['CLIENT_KEY'],
            client_secret=self.config['CLIENT_SECRET']
        )
        
        params = {
            'client_key': self.config['CLIENT_KEY'],  # TikTok uses client_key instead of client_id in the URL
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'redirect_uri': self.redirect_uri,
            'state': secrets.token_urlsafe(16),
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256'
        }
        
        url = service.get_authorize_url(**params)
        
        session = service.get_auth_session(data={
            'code': self.code_challenge,
            'redirect_uri': self.redirect_uri
        })
        
        return session
        
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
    
    def upload_to_tiktok(self):
        """
        Parse the content to TikTok 
        """
        pass

