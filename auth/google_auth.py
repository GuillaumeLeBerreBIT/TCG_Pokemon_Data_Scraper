import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

class GoogleAuth:
    
    CLIENTS_SECRETS_FILE = './token/client_secret.json'
    TOKEN_PICKLE_FILE = './token/token.pickle'
    
    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/drive.metadata.readonly"
    ]
    
    @classmethod
    def get_credentials(cls):
        
        credentials = None
        
        if os.path.exists(cls.TOKEN_PICKLE_FILE):
            try:
                with open(cls.TOKEN_PICKLE_FILE, 'rb') as token:
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
                                                                    cls.SCOPES)
                credentials = flow.run_local_server(port=8080)
                
            with open(cls.TOKEN_PICKLE_FILE, 'wb') as token:
                pickle.dump(credentials, token)
    
        return credentials