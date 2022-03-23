import tweepy
import os
import time
from threading import Timer
import requests
import json

from io import StringIO
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from email.utils import parsedate_to_datetime


TWITTER_HANDLE = 'alrocar'

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
ACCESS_TOKEN_SECRET = os.environ['ACCESS_TOKEN_SECRET']
TB_TOKEN = os.environ['TB_TOKEN']
READ_TOKEN = os.environ['READ_TOKEN']

TB_API_URL = 'https://api.tinybird.co/v0'
datasource = 'tweets'

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, timeout=300)


def get_requests_session():
    retry = Retry(total=5, backoff_factor=10)
    adapter = HTTPAdapter(max_retries=retry)
    _session = requests.Session()
    _session.mount('http://', adapter)
    _session.mount('https://', adapter)
    return _session


class TinybirdApiSink():
    def __init__(self, token, datasource, endpoint=TB_API_URL):
        super().__init__()
        self.endpoint = endpoint
        self.token = token
        self.datasource = datasource
        self.url = f'{self.endpoint}/datasources?mode=append&name={self.datasource}&format=ndjson'
        retry = Retry(total=5, backoff_factor=0.2)
        adapter = HTTPAdapter(max_retries=retry)
        self._session = requests.Session()
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)
        self.reset()
        self.wait = False

    def reset(self):
        self.chunk = StringIO()

    def append(self, value):
        try:
            self.chunk.write(json.dumps(value) + '\n')
        except Exception as e:
            print(e)

    def tell(self):
        return self.chunk.tell()

    def flush(self):
        self.wait = True
        data = self.chunk.getvalue()
        # f = open("sample.ndjson", "w")
        # f.write(data)
        # f.close()
        # import sys
        # sys.exit(0)
        self.reset()
        headers = {
            'Authorization': f'Bearer {self.token}',
            # 'X-TB-Client': f'{__version__.__name__}-{__version__.__version__}',
        }

        ok = False
        try:
            response = self._session.post(self.url, headers=headers, files=dict(ndjson=data))
            print('flush response')
            print(response)
            ok = response.status_code < 400
            self.wait = False
            return ok
        except Exception as e:
            self.wait = False
            print(e)
            return ok


class MyStreamListener(tweepy.StreamListener):

    def __init__(self, name, api, search_term, max_wait_seconds=10,
                 max_wait_records=10000,
                 max_wait_bytes=1024*1024*1):
        self.name = name
        self.records = 0
        self.api = api
        self.search_term = search_term
        self.sink = TinybirdApiSink(TB_TOKEN, datasource)
        self.max_wait_seconds = max_wait_seconds
        self.max_wait_records = max_wait_records
        self.max_wait_bytes = max_wait_bytes
        self.records = 0
        self.timer = None
        self.timer_start = None
        self.tr_timer = None
        self.tr_timer_start = None

    def append(self, record):
        if self.records % 100 == 0:
            print('append')
        self.sink.append(record)
        self.records += 1
        if self.records < self.max_wait_records and self.sink.tell() < self.max_wait_bytes:
            if not self.timer:
                self.timer_start = time.monotonic()
                self.timer = Timer(self.max_wait_seconds, self.flush)
                self.timer.name = f"f{self.name}_timer"
                self.timer.start()
        else:
            self.flush()

    def flush(self):
        print('flush')
        if self.timer:
            self.timer.cancel()
            self.timer = None
            self.timer_start = None
        if not self.records:
            return
        self.sink.flush()
        self.records = 0

    def on_data(self, raw_data):
        while self.sink.wait:
            print('wait flush')
            print(self.search_term)
            time.sleep(1)
        super().on_data(raw_data)
        tweet = json.loads(raw_data)
        if 'created_at' not in tweet or 'id' not in tweet or 'text' not in tweet:
            return
        date = str(tweet['created_at'])

        text = ''
        try:
            if tweet['truncated']:
                text = tweet['extended_tweet']['full_text']
            else:
                text = tweet['text']
        except Exception as e:
            print(e)
        
        try:
            if tweet.get('retweeted_status'):
                if tweet.get('retweeted_status')['truncated']:
                    text += tweet['retweeted_status'].get('extended_tweet', {})['full_text']
                else:
                    text += tweet['retweeted_status'].get('text')
        except Exception as e:
            print(e)
        
        try:
            if tweet.get('quoted_status'):
                q = tweet.get('quoted_status')
                if q['truncated']:
                    text += q.get('extended_tweet', {})['full_text']
                else:
                    text += q.get('text')
        except Exception as e:
            print(e)
                
        tw = {
            "search_term": self.search_term,
            "tweet": text,
            "date": parsedate_to_datetime(date).strftime("%Y-%m-%d %H:%M:%S")
        }
        self.append(tw)
        


def connect():
    try:
        # myStreamListener = MyStreamListener('tweets', api, 'covid', max_wait_seconds=10)
        myStreamListener = MyStreamListener('tweets', api, 'Merry Christmas', max_wait_seconds=2)
        # myStreamListener = MyStreamListener('tweets', api, 'crypto')
        myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener)

        # myStream.filter(track=['covid', 'coronavirus', 'omicron', 'vaccine', 'covid-19', 'COVID19', 'Omicron', 'Vaccine', 'pandemic', 'Pandemic', 'Covid', 'COVID-19', 'Ómicron'])
        myStream.filter(track=['2022', '2021', 'christmas', 'Navidad', 'Happy New Year', 'Merry Xmas', 'happy new year', 'Christmas', "Happy New Year's Eve"])
        # myStream.filter(track=['NFT', 'crypto', 'ethereum', 'bitcoin', 'eth', 'blockchain', 'polygon', 'token', 'ATH', 'FOMO', 'ICO', 'mining', 'satoshi'])
    except Exception as e:
        print(e)


while True:
    print('connect')
    connect()