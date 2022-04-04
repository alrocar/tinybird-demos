import os
import pathlib
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import numpy as np
import tweepy
from PIL import Image, ImageDraw, ImageFont
from tb.api import API
from tb.datasource import Datasource
from textblob import TextBlob
from textblob.exceptions import TranslatorError

from colors import shift_hue

CONSUMER_KEY = os.environ['AVATAR_CONSUMER_KEY']
CONSUMER_SECRET = os.environ['AVATAR_CONSUMER_SECRET']
ACCESS_TOKEN = os.environ['AVATAR_ACCESS_TOKEN']
ACCESS_TOKEN_SECRET = os.environ['AVATAR_ACCESS_TOKEN_SECRET']
TB_TOKEN = os.environ['AVATAR_TBB_TOKEN']
READ_TOKEN = os.environ['AVATAR_READ_TOKEN']

TBCONSUMER_KEY = os.environ['TBAVATAR_CONSUMER_KEY']
TBCONSUMER_SECRET = os.environ['TBAVATAR_CONSUMER_SECRET']
TBACCESS_TOKEN = os.environ['TBAVATAR_ACCESS_TOKEN']
TBACCESS_TOKEN_SECRET = os.environ['TBAVATAR_ACCESS_TOKEN_SECRET']

datasource = f'tweets'

config = {
    'alrocar': {
        'consumer_key': CONSUMER_KEY,
        'consumer_secret': CONSUMER_SECRET,
        'access_token': ACCESS_TOKEN,
        'access_token_secret': ACCESS_TOKEN_SECRET,
        'tb_token': TB_TOKEN,
        'tb_read_token': READ_TOKEN
    },
    'tinybirdco': {
        'consumer_key': TBCONSUMER_KEY,
        'consumer_secret': TBCONSUMER_SECRET,
        'access_token': TBACCESS_TOKEN,
        'access_token_secret': TBACCESS_TOKEN_SECRET,
        'tb_token': TB_TOKEN,
        'tb_read_token': READ_TOKEN,
        'id': 1501914178298261500
    }
}


def get_last_tweet_id(tb_api, batch):
    max_id_url = f'pipes/timeline_max_id.json?batch={batch}'
    response = tb_api.get(max_id_url)
    data = response.json()['data']
    if len(data) == 0:
        return
    return data[0]['since_id']


def get_emoji(tb_api, batch, limit=1):
    url = f'pipes/emoji_count_endpoint.json?search_term={batch}&result_limit={limit}'
    response = tb_api.get(url)
    data = response.json()['data']
    if len(data) == 0:
        return
    return data


def get_polarity_mvng_avg(tb_api, batch):
    max_id_url = f'pipes/timeline_moving_average.json?batch={batch}'
    response = tb_api.get(max_id_url)
    data = response.json()['data']
    if len(data) == 0:
        return
    return data



def get_tweets(api, since_id=None, user=None):
    raw = []
    # if user:
    #     for page in tweepy.Cursor(api.user_timeline, user_id=user, count=200, exclude_replies=False, inclure_rts=True).pages(1):
    #         for tweet in page:
    #                 raw.append(tweet)
    #     for page in tweepy.Cursor(api.mentions_timeline, count=200).pages(1):
    #         for tweet in page:
    #                 raw.append(tweet)
    # else:
    # if user == 'alrocar':
    if since_id:
        for page in tweepy.Cursor(api.home_timeline, since_id=since_id, count=200, exclude_replies=False).pages(1):
            for tweet in page:
                raw.append(tweet)
    else:
        for page in tweepy.Cursor(api.home_timeline, count=200, exclude_replies=False).pages(5):
            for tweet in page:
                raw.append(tweet)
    # else:
    #     uu = api.get_user(username=user, user_auth=True)
    #     result = api.get_users_mentions(id=uu.data.id, max_results=100, since_id=since_id, user_auth=True, tweet_fields=['text', 'created_at', 'id'])
    #     for res in result.data:
    #         raw.append({'truncated': False, 'text': res.text, 'created_at': res.created_at, 'id': res.id})

    #     result = api.get_users_tweets(id=uu.data.id, max_results=100, since_id=since_id, user_auth=True, tweet_fields=['text', 'created_at', 'id'])
    #     for res in result.data:
    #         raw.append({'truncated': False, 'text': res.text, 'created_at': res.created_at, 'id': res.id})
    
    return raw


def parse_tweets(tweets):
    result = []
    for tweet in tweets:
        tweetid = tweet.id
        tweetdate = str(tweet.created_at)
        tweettext = tweet.text
        tt = " ".join(re.sub("([^0-9A-Za-z \t])|(\w+:\/\/\S+)", "", tweettext).split())
        result.append([tweetid, tweetdate, tt])
    return result


def enrich_polarity(tweet):
    try:
        analysis = TextBlob(tweet)
        language = analysis.detect_language()
        if language != 'en':
            analysis = analysis.translate(to='en')
        return round(analysis.sentiment.polarity, 4)
    except TranslatorError:
        try:
            return round(analysis.sentiment.polarity, 4)
        except:
            return 0
    except Exception:
        try:
            return round(analysis.sentiment.polarity, 4)
        except:
            return 0


def to_tinybird(rows, datasource_name, token=TB_TOKEN):
    if rows:
        with Datasource(datasource_name, token) as ds:
            for row in rows:
                ds << row


def get_polarity(tb_api, batch):
    polarity_url = f'pipes/timeline_polarity.json?batch={batch}'
    response = tb_api.get(polarity_url)
    data = response.json()['data']
    if len(data) == 0 or data[0]['polarity'] is None:
        return
    return float(data[0]['polarity'])


def polarity2hue(polarity):
    rr = 3
    min = 0
    max = 180 - 78
    range = max - min
    step = range / rr
    step_polarity = 200 / rr
    return (polarity + 100) / step_polarity * step / 360 #* 1.8/720


def update_avatar(hue, polarity, api, emoji):
    path = pathlib.Path(__file__).parent.absolute()
    img = Image.open(f'{path}/avatar.png').convert('RGBA')
    arr = np.array(img)
    new_img = Image.fromarray(shift_hue(arr, hue), 'RGBA')
    avatar = f'_avatar.png'
    # fnt = ImageFont.truetype(f'{path}/NotoColorEmoji.ttf', size=109, layout_engine=ImageFont.LAYOUT_RAQM)
    # draw = ImageDraw.Draw(new_img)
    # draw.text((430, 400), emoji, fill="#faa", embedded_color=True, font=fnt)
    # draw.text((580, 420), emoji, fill="#faa", embedded_color=True, font=fnt)
    new_img.save(avatar)

    shape = [(10, 10), (140, 140)]
    
    # creating new Image object
    arc = Image.new("RGBA", (130, 130))

    # create rectangle image
    img1 = ImageDraw.Draw(arc)  
    img1.arc(shape, end = 360 - 60, start = 360 - 120, fill ="black", width=14)

    if polarity:
        rr = True if polarity > 0 else False
        rtat = -50 if rr else 0
        arc = arc.rotate(180 if rr else 0)
        arc = arc.resize((200, 70), Image.ANTIALIAS)
        

        new_img = new_img.convert('RGBA')
        new_img.paste(arc, (475, 638 + rtat), arc)

    # Image.Image.paste(new_img, rgba, (475, 638))
    new_img.save(avatar)
    

    api.update_profile_image(avatar)


def update_header(api):
    path = pathlib.Path(__file__).parent.absolute()
    api.update_profile_banner(f'{path}/stripes.png')


def create_stripes(data, emojis):
    path = pathlib.Path(__file__).parent.absolute()
    stripes = Image.new(mode="RGB", size=(1500, 500))
    i = 0
    import math
    fnt = ImageFont.truetype(f'{path}/NotoColorEmoji.ttf', size=109, layout_engine=ImageFont.LAYOUT_RAQM)
    emojis.reverse()
    for p, emoji in zip(data, emojis):
        img = Image.open(f'{path}/stripe.png').convert('RGBA')
        aa = img.load()
        # hues = [[103,0,13], [165,15,21], [203,24,29], [239,59,44], [251,106,74], [252,146,114], [252,187,161], [254,224,210], [255,245,240], [247,251,255], [222,235,247], [198,219,239], [158,202,225], [107,174,214], [66,146,198], [33,113,181], [8,81,156], [8,48,107]]       
        hues = [[103,0,13], [165,15,21], [203,24,29], [239,59,44], [251,106,74], [252,146,114], [252,187,161], [254,224,210], [255,245,240], [247,252,245],[229,245,224],[199,233,192],[161,217,155],[116,196,118],[65,171,93],[35,139,69],[0,109,44],[0,68,27]]
        # hues = [[222,45,38],[252,146,114],[254,224,210], [229,245,224], [161,217,155], [49,163,84]]
        

        data = np.array(img)

        # r1, g1, b1 = 0, 0, 0 # Original value
        r1 = aa[0, 0][0] # Original value
        g1 = aa[0, 0][1] # Original value
        b1 = aa[0, 0][2] # Original value
        r2, g2, b2 = 255 - p['polarity'] + 100, 0 + p['polarity'] + 100, 0 # Value that we want to replace it with
        hue = hues[math.floor((p['polarity'] + 100) / (200 / len(hues))) % len(hues)]
        r2 = hue[0]
        g2 = hue[1]
        b2 = hue[2]

        red, green, blue = data[:,:,0], data[:,:,1], data[:,:,2]
        mask = (red == r1) & (green == g1) & (blue == b1)
        data[:,:,:3][mask] = [r2, g2, b2]

        new_img = Image.fromarray(data)
        
        Image.Image.paste(stripes, new_img, (10 * i, 0))
        # icon = Image.new(mode="RGB", size=(140, 140))
        # draw = ImageDraw.Draw(icon)
        # draw.text((0, 0), emoji['emoji'], fill="#faa", embedded_color=True, font=fnt)
        # out = icon.resize((10, 10))
        # rgba = out.convert("RGBA")
        # datas = rgba.getdata()
        
        # newData = []
        # for item in datas:
        #     if item[0] == 0 and item[1] == 0 and item[2] == 0: 
        #         newData.append((r2, g2, b2, 0))
        #     else:
        #         newData.append(item)
        
        # rgba.putdata(newData)
        # Image.Image.paste(stripes, rgba, (10*i, int(p['polarity'] * -2.50 + 250)))
        i += 1
    stripes.save(f'{path}/stripes.png')


def run():
    for batch in config:
        # if batch == 'alrocar':
        #     continue
        print(batch)
        cc = config[batch]
        # if batch == 'alrocar':
        auth = tweepy.OAuthHandler(cc['consumer_key'], cc['consumer_secret'])
        auth.set_access_token(cc['access_token'], cc['access_token_secret'])
        api = tweepy.API(auth, timeout=300)
        # else:
        #     api = tweepy.Client(
        #         consumer_key=cc['consumer_key'],
        #         consumer_secret=cc['consumer_secret'],
        #         access_token=cc['access_token'],
        #         access_token_secret=cc['access_token_secret'],)

        tb_api = API(cc['tb_token'])
        
        since_id = get_last_tweet_id(tb_api, batch)
        tweets_raw = get_tweets(api, since_id, batch)
        tweets = []
        tt = []
        for tweet in tweets_raw:
            tweet = getattr(tweet, '_json', tweet)
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
            # text = " ".join(re.sub("([^0-9A-Za-z \t])|(\w+:\/\/\S+)", "", text).split())
            if text:
                t = {
                        'search_term': batch,
                        'batch': batch,
                        'id': tweet['id'],
                        'date': parsedate_to_datetime(str(tweet['created_at'])).strftime("%Y-%m-%d %H:%M:%S") if not isinstance(tweet['created_at'], datetime) else str(tweet['created_at']),
                        'text': text,
                        'polarity': enrich_polarity(text),
                        'tweet': text
                    }
                tweets.append(t)
                tt.append(
                    {
                        'batch': t['batch'],
                        'id': tweet['id'],
                        'date': t['date'],
                        'text': text,
                        'polarity': t['polarity']
                    })
        to_tinybird(tt, datasource, token=cc['tb_token'])
        to_tinybird(tweets, 'tweets_s__v0', token=cc['tb_token'])
        polarity = get_polarity(tb_api, batch)
        if polarity:
            hue = polarity2hue(polarity)
            emoji = get_emoji(tb_api, batch)[0]['emoji']
            if batch == 'alrocar':
                update_avatar(hue, polarity, api, emoji)
            to_tinybird([{'batch': batch, 'date': str(datetime.now()), 'polarity': polarity, 'hue': hue}], 'polarity_log')

        data = get_polarity_mvng_avg(tb_api, batch)
        emojis = get_emoji(tb_api, batch, limit=150)
        create_stripes(data, emojis)
        update_header(api)
