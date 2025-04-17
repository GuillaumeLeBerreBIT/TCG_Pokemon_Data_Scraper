from dotenv import dotenv_values
from oauthlib.oauth2 import WebApplicationClient
import requests
import os 
import math

class UploadContent:
    
    def __init__(self, content):
        
        self.config = dotenv_values('.env')
        self.content = content
        self.headers = {
            'Authorization': f'Bearer {self.config['ACCESS_TOKEN']}',
            'Content-Type': 'application/json'
        }
        
        self.videosize = os.path.getsize(self.content)
        self.chunck_size = 5 * 1024 * 1024
        self.total_chunk_count = math.ceil(self.videosize / self.chunck_size)
    
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
            response.raise_for_status()
            
            
            return response
        
        except requests.exceptions.HTTPError as e:
            
            raise SystemExit(e)
            
    def fetch_o_auth(self):
        """
        Fetch the OAuth 2.0 Token
        """
        client = WebApplicationClient(self.config['CLIENT_ID'])
        
        authorization_url = 'https://www.tiktok.com/v2/auth/authorize/'
        
        url = client.prepare_request_uri(
            authorization_url,
            redirect_uri='http://127.0.0.1:5000/callback/',
            scope=['user.info.basic', 'video.upload', 'video.publish'],
            state='D8VAo311AAl_49LAtM51HA',
        )
        
        
    
    def upload_to_tiktok(self):
        """
        Parse the content to TikTok 
        """
        pass

