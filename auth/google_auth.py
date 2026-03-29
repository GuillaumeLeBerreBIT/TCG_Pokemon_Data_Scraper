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
        "https://www.googleapis.com/auth/drive"
    ]
    
    @classmethod
    def get_credentials(cls, token_file, scopes):
        
        credentials = None
        
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