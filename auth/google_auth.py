import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

class GoogleAuth:
    
    CLIENTS_SECRETS_FILE = './token/client_secret.json'    
    
    @classmethod
    def get_credentials(cls, token_file, scopes, instance='YOUTUBE'):
        
        credentials = None
        client_id = os.getenv(f'{instance}_CLIENT_ID')
        client_secret = os.getenv(f'{instance}_CLIENT_SECRET')
        refresh_token = os.getenv(f'{instance}_REFRESH_TOKEN')

        if client_id and client_secret and refresh_token:
                try:
                    credentials = Credentials(
                        token=None,
                        refresh_token=os.getenv(f'{instance}_REFRESH_TOKEN'),
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=os.getenv(f'{instance}_CLIENT_ID'),
                        client_secret=os.getenv(f'{instance}_CLIENT_SECRET'),
                        scopes=scopes
                        )
                    
                    credentials.refresh(Request())
                except (RefreshError, ValueError) as e:
                    raise Exception('Unable to retrieve the correct credentials.')
        
        if os.path.exists(token_file):
            try:
                with open(token_file, 'rb') as token:
                    credentials = pickle.load(token)
                    
            except (pickle.UnpicklingError, EOFError):
                pass
            
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    credentials = None
            
            if not credentials or not credentials.valid:
                flow = InstalledAppFlow.from_client_secrets_file(cls.CLIENTS_SECRETS_FILE,
                                                                    scopes)
                credentials = flow.run_local_server(port=8080)
                
            with open(token_file, 'wb') as token:
                pickle.dump(credentials, token)
    
        return credentials