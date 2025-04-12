from flask import Flask, request, redirect, url_for

app = Flask(__name__)

# Home route to initiate the login process
@app.route('/')
def index():
    return '<a href="/login">Login with TikTok</a>'

# Route to redirect the user to TikTok's OAuth endpoint
@app.route('/login')
def login():
    # Replace these values with your application's credentials and desired scopes
    client_id = 'sbawd15l5wth8kl3wi'
    redirect_uri = 'http://localhost:5000/auth/tiktok/callback'  # This must match your registered Redirect URI
    state = 'SOME_RANDOM_STRING_FOR_CSRF_PROTECTION'  # Optional but recommended for security
    scope = 'user.info.basic'  # Adjust scope as needed

    # Build TikTok's OAuth URL according to their API documentation
    tiktok_oauth_url = (
        f"https://open-api.tiktok.com/platform/oauth/connect/?"
        f"client_key={client_id}&scope={scope}&redirect_uri={redirect_uri}"
        f"&response_type=code&state={state}"
    )
    return redirect(tiktok_oauth_url)

# This route will receive the callback from TikTok after the user authorizes your app
@app.route('/auth/tiktok/callback')
def tiktok_callback():
    error = request.args.get('error')
    if error:
        return f"Error: {error}"

    # Retrieve the authorization code and state parameters
    code = request.args.get('code')
    state = request.args.get('state')

    # For security, you should verify that the received 'state' matches the one you sent.
    # In a real application, exchange 'code' for an access token with TikTok's API.
    # Example: call a function like exchange_code_for_token(code)

    return (
        f"<h2>OAuth Callback Received</h2>"
        f"<p>Authorization Code: {code}</p>"
        f"<p>State: {state}</p>"
        f"<p>Now you would exchange the authorization code for an access token.</p>"
    )

if __name__ == '__main__':
    app.run(debug=True)
