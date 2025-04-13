from dotenv import dotenv_values
import requests

class UploadContent:
    
    def __init__(self, content):
        
        self.config = dotenv_values('.env')
        self.content = content
    
    def upload_to_tiktok(self):
        """
        Upload a video to TikTok
        """

    