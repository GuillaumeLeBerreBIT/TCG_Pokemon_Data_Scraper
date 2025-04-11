import requests

class UploadContent:
    
    def __init__(self, content, key, secret):
        
        
        self.content = content
        
        self.key = key
        self.secret = secret
    
    def upload_to_tiktok(self):
        """
        Upload a video to TikTok
        """
    
    