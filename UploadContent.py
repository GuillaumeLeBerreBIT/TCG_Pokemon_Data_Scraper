from dotenv import dotenv_values
import requests

class UploadContent:
    
    def __init__(self, content):
        
        self.config = dotenv_values('.env')
        self.content = content
        self.headers = {
            'Authorization': f'Bearer {self.config['ACCES_TOKEN']}',
            'Content-Type': 'application/json'
        }
    
    def extract_upload_info(self):
        """
        Do a POST request to catch the Upload URL and the Publish ID from the response 
        """
        
        try: 
            
            url = 'https://open.tiktokapis.com/v2/post/publish/inbox/video/init/'
            data = {
                "source": "FILE_UPLOAD",
                "video_size": "exampleVideoSize",  # Replace with actual size as integer
                "chunk_size": "exampleVideoSize",  # Replace with actual size as integer
                "total_chunk_count": 1
            }
            
            response = requests.post(url=url, json=data, headers=self.headers)
            response.raise_for_status()
            
            
            return response
        
        except requests.exceptions.HTTPError as e:
            
            raise SystemExit(e)
            
    
    def upload_to_tiktok(self):
        """
        
        """
        

    