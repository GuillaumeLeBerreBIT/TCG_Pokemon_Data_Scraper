from flask import Flask, request, redirect, make_response, render_template, session
from dotenv import dotenv_values
import secrets
import hashlib
import base64
import requests
import os
import string

config = dotenv_values(".env")

app = Flask(__name__)
app.secret_key = 'SomeFixedCodeVerifier1234567890abcdefghijklmnopqrstuvwxyz'  # Replace with a strong random key

def generate_code_verifier(length=64):
    allowed_chars = string.ascii_letters + string.digits + "-._~"
    return ''.join(secrets.choice(allowed_chars) for _ in range(length))

def generate_code_challenge(verifier):
    # Generate the hex-encoded SHA256 hash as the code challenge
    return hashlib.sha256(verifier.encode('utf-8')).hexdigest()

# Configuration
CLIENT_KEY = config['CLIENT_KEY']
CLIENT_SECRET = config['CLIENT_SECRET']
SERVER_ENDPOINT_REDIRECT = 'http://127.0.0.1:5000/callback/'

@app.route('/')
def index():
    return '<h1>TikTok OAuth Demo</h1><a href="/oauth">Connect with TikTok</a>'

@app.route('/oauth')
def oauth():
    # Generate a new code verifier for this session
    code_verifier = generate_code_verifier()
    session['code_verifier'] = code_verifier
    
    # Generate the code challenge
    code_challenge = generate_code_challenge(code_verifier)
    
    # Generate a CSRF state token
    csrf_state = secrets.token_urlsafe(16)
    session['csrf_state'] = csrf_state
    
    # For debugging, print what we're storing
    print(f"Generated code_verifier: {code_verifier}")
    print(f"Generated code_challenge: {code_challenge}")
    
    # Build the TikTok authorization URL
    auth_url = 'https://www.tiktok.com/v2/auth/authorize/'
    auth_url += f'?client_key={CLIENT_KEY}'
    auth_url += '&scope=user.info.basic,video.upload,video.publish'
    auth_url += '&response_type=code'
    auth_url += f'&redirect_uri={SERVER_ENDPOINT_REDIRECT}'
    auth_url += f'&state={csrf_state}'
    auth_url += f'&code_challenge={code_challenge}'
    auth_url += '&code_challenge_method=S256'
    
    return redirect(auth_url)

@app.route('/callback/')
def callback():
    # Get the authorization code from the request
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Get the code verifier from the session
    code_verifier = session.get('code_verifier')
    
    # For debugging
    print(f"Retrieved code_verifier from session: {code_verifier}")
    
    # Verify CSRF state
    stored_state = session.get('csrf_state')
    if not stored_state or stored_state != state:
        return "CSRF verification failed", 403
    
    if not code_verifier:
        return "Code verifier not found in session", 400
    
    # Exchange authorization code for access token
    if code:
        token_url = 'https://open.tiktokapis.com/v2/oauth/token/'
        payload = {
            'client_key': CLIENT_KEY,
            'client_secret': CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': SERVER_ENDPOINT_REDIRECT,
            'code_verifier': code_verifier
        }
        
        # For debugging
        print(f"Sending payload to token endpoint: {payload}")
        
        response = requests.post(token_url, data=payload)
        token_data = response.json()
        
        return f"Full response: {token_data}"
    
    return "Authorization failed", 400

if __name__ == '__main__':
    app.run(debug=True)