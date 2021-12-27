from flask import Flask, redirect, request
import tweepy
import os

 
app = Flask(__name__)
 
@app.route('/')
def login():
    key = os.getenv('CONSUMER_KEY')
    secret = os.getenv('CONSUMER_SECRET')
    auth = tweepy.OAuthHandler(key, secret, 'https://emojis-wrapped.herokuapp.com/auth')
    redirect_url = auth.get_authorization_url()
    return redirect(redirect_url, code=302)
    

@app.route('/auth')
def auth():
    key = os.getenv('CONSUMER_KEY')
    secret = os.getenv('CONSUMER_SECRET')
    auth = tweepy.OAuthHandler(key, secret, 'https://emojis-wrapped.herokuapp.com/auth')
    oauth_token = request.args.get('oauth_token', type=str)
    oauth_verifier = request.args.get('oauth_verifier', type=str)
    auth.request_token = {
        'oauth_token' : oauth_token,
        'oauth_token_secret' : oauth_verifier
    }
    result = auth.get_access_token(oauth_verifier)
    auth.set_access_token(result[0], result[1])
    api = tweepy.API(auth)
    user = api.verify_credentials()
    return repr(user)
 

if __name__ == '__main__':
    app.run()
