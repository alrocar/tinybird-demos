from flask import Flask, redirect, request
import tweepy
import os
from io import StringIO
import datetime
import time
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

 
app = Flask(__name__)


def get_requests_session():
    retry = Retry(total=5, backoff_factor=10)
    adapter = HTTPAdapter(max_retries=retry)
    _session = requests.Session()
    _session.mount('http://', adapter)
    _session.mount('https://', adapter)
    return _session

 
@app.route('/')
def login():
    screen_name = request.args.get('screen_name', type=str)
    if screen_name:
        status = get_data(screen_name)
        if status is None:
            return do_login()
        else:
            return status
    else:
        return do_login()


def do_login():
    key = os.getenv('CONSUMER_KEY')
    secret = os.getenv('CONSUMER_SECRET')
    auth = tweepy.OAuthHandler(key, secret, 'https://emojis-wrapped.herokuapp.com/auth')
    redirect_url = auth.get_authorization_url()
    return redirect(redirect_url, code=302)


def get_data(user_name):
    token = os.getenv('TB_TOKEN')
    api_url = os.getenv('TB_API_URL')

    response = get_requests_session().post(f'{api_url}/pipes/users_status.json?token={token}&user_name={user_name}')
    data = response.json()['data']
    
    if data is None:
        return None

    response = get_requests_session().post(f'{api_url}/pipes/users_data.json?token={token}&user_name={user_name}')
    return {'tb_user': data[0], 'data': response.json()['data']}
    

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
    tb_user = to_tinybird(user.screen_name, 'new', result[0], result[1])
    import subprocess
    subprocess.Popen(["python3", "batch.py"])
    return {'tb_user': tb_user, 'tw_user': user._json}


def to_tinybird(user_name, status, oauth_token, oauth_secret):
    token = os.getenv('TB_TOKEN')
    api_url = os.getenv('TB_API_URL')

    url = f'{api_url}/datasources?mode=append&name=user&format=ndjson'

    chunk = StringIO()
    user = {
        'date': str(datetime.datetime.now()),
        'user_name': user_name,
        'status': status,
        'oauth_token': oauth_token,
        'oauth_secret': oauth_secret
    }
    chunk.write(json.dumps(user))

    data = chunk.getvalue()
    headers = {
        'Authorization': f'Bearer {token}'
    }

    if data:
        status_code = 429
        retry = 0
        while status_code == 429 and retry < 5:
            response = get_requests_session().post(url, headers=headers, files=dict(ndjson=data))
            status_code = response.status_code
            if status_code == 429:
                time.sleep(5)
                retry += 1
        ok = response.status_code < 400
        if not ok:
            raise Exception(json.dumps(response.json()))

    return user
 

if __name__ == '__main__':
    app.run()
