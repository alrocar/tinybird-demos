# - get from user where status = 'new'
# - create threadpool with n workers

import tweepy
import time
import json
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import StringIO
import datetime
import os


key = os.getenv('CONSUMER_KEY')
secret = os.getenv('CONSUMER_SECRET')
TB_TOKEN = os.getenv('TB_TOKEN')
TB_API_URL = os.getenv('TB_API_URL')


def get_requests_session():
    retry = Retry(total=5, backoff_factor=10)
    adapter = HTTPAdapter(max_retries=retry)
    _session = requests.Session()
    _session.mount('http://', adapter)
    _session.mount('https://', adapter)
    return _session


def get_users():
    response = get_requests_session().get(f'{TB_API_URL}/pipes/users_status.json?token={TB_TOKEN}&status=new')
    users = response.json()['data']
    for user in users:
        try:
            logging.info(f'new user: {user["user_name"]}')
            tweets = get_tweets(user['user_name'], user['oauth_token'], user['oauth_secret'])
            update_status(user, 'working')
            to_tinybird(user['user_name'], tweets)
            call_pupeteer(user['user_name'])
            update_status(user, 'done')
        except Exception as e:
            logging.exception(e)
            update_status(user, f'error: {str(e)}')


def get_tweets(user_name, oauth_token, oauth_secret):
    auth = tweepy.OAuthHandler(key, secret, 'https://emojis-wrapped.herokuapp.com/auth')
    auth.set_access_token(oauth_token, oauth_secret)
    api = tweepy.API(auth)

    raw = []
    max_id = None
    i = 0
    ff = False
    for page in tweepy.Cursor(api.user_timeline, max_id=max_id, count=200).pages(900):
        if ff:
            break
        for tweet in page:
            try:
                max_id = tweet.id_str
                created_at = tweet.created_at
                if created_at.year > 2021:
                    continue
                if created_at.year < 2021:
                    ff = True
                if ff:
                    break
                raw.append(json.dumps({
                    'tweet': tweet._json,
                    'date': str(created_at),
                    'search_term': user_name
                }))
            except Exception as e:
                logging.exception(e)
        i += 1
        logging.info(f'{str(i)}')

    max_id = None
    ff = False
    for page in tweepy.Cursor(api.mentions_timeline, max_id=max_id, count=200).pages(75):
        if ff:
            break
        for tweet in page:
            try:
                max_id = tweet.id_str
                created_at = tweet.created_at
                if created_at.year > 2021:
                    continue
                if created_at.year < 2021:
                    ff = True
                if ff:
                    break
                raw.append(json.dumps({
                    'tweet': tweet._json,
                    'date': str(created_at),
                    'search_term': user_name
                }))
            except Exception as e:
                logging.exception(e)
        i += 1
        logging.info(f'{str(i)}')

    max_id = None
    ff = False
    for page in tweepy.Cursor(api.get_favorites, max_id=max_id, count=200).pages(75):
        if ff:
            break
        for tweet in page:
            try:
                max_id = tweet.id_str
                created_at = tweet.created_at
                if created_at.year < 2021:
                    ff = True
                if ff:
                    break
                raw.append(json.dumps({
                    'tweet': tweet._json,
                    'date': str(created_at),
                    'search_term': user_name
                }))
            except Exception as e:
                logging.exception(e)
        i += 1
        logging.info(f'{str(i)}')
    return raw


def to_tinybird(user_name, tweets):
    url = f'{TB_API_URL}/datasources?mode=append&name=tweets__v1&format=ndjson'

    chunk = StringIO()
    for tweet in tweets:
        chunk.write(json.dumps({
            'date': str(datetime.datetime.now()),
            'search_term': user_name,
            'tweet': tweet
        }))

        if chunk.tell() > 7 * (1024 ** 2):
            data = chunk.getvalue()
            headers = {
                'Authorization': f'Bearer {TB_TOKEN}'
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

            chunk.seek(0)
            chunk.truncate()

    data = chunk.getvalue()
    headers = {
        'Authorization': f'Bearer {TB_TOKEN}'
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


def update_status(user, status):
    url = f'{TB_API_URL}/datasources?mode=append&name=users&format=ndjson'

    chunk = StringIO()
    user = {
        'date': str(datetime.datetime.now()),
        'user_name': user['user_name'],
        'status': status,
        'oauth_token': user['oauth_token'],
        'oauth_secret': user['oauth_secret']
    }
    chunk.write(json.dumps(user))

    data = chunk.getvalue()
    headers = {
        'Authorization': f'Bearer {TB_TOKEN}'
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


def call_pupeteer(user_name):
    logging.info('call puppeteer')


get_users()
