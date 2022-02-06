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

datasource = f'tweets'

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, timeout=300)
tb_api = API(TB_TOKEN)
batch = 'alrocar'


def get_last_tweet_id(tb_api):
    max_id_url = f'pipes/timeline_max_id.json?batch={batch}'
    response = tb_api.get(max_id_url)
    data = response.json()['data']
    if len(data) == 0:
        return
    return data[0]['since_id']


def get_emoji(tb_api, limit=1):
    url = f'pipes/emoji_count_endpoint.json?search_term={batch}&result_limit={limit}'
    response = tb_api.get(url)
    data = response.json()['data']
    if len(data) == 0:
        return
    return data


def get_polarity_mvng_avg(tb_api):
    max_id_url = f'pipes/timeline_moving_average.json?batch={batch}'
    response = tb_api.get(max_id_url)
    data = response.json()['data']
    if len(data) == 0:
        return
    return data


def get_tweets(since_id=None, user=None):
    raw = []
    # for page in tweepy.Cursor(api.user_timeline, id=batch, count=200, exclude_replies=False).pages(15):
    for page in tweepy.Cursor(api.home_timeline, since_id=since_id, count=200, exclude_replies=False).pages(15):
        for tweet in page:
            raw.append(tweet)
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


def get_polarity(tb_api):
    polarity_url = f'pipes/timeline_polarity.json?batch={batch}'
    response = tb_api.get(polarity_url)
    data = response.json()['data']
    if len(data) == 0 or data[0]['polarity'] is None:
        return
    return float(data[0]['polarity'])


def polarity2hue(polarity):
    rr = 18
    min = 0
    max = 180 - 78
    range = max - min
    step = range / rr
    step_polarity = 200 / rr
    return (polarity + 100) / step_polarity * step / 360 #* 1.8/720


def update_avatar(hue, polarity, emoji):
    path = pathlib.Path(__file__).parent.absolute()
    img = Image.open(f'{path}/avatar.png').convert('RGBA')
    arr = np.array(img)
    new_img = Image.fromarray(shift_hue(arr, hue), 'RGBA')
    avatar = f'_avatar.png'
    fnt = ImageFont.truetype(f'{path}/NotoColorEmoji.ttf', size=109, layout_engine=ImageFont.LAYOUT_RAQM)
    draw = ImageDraw.Draw(new_img)
    draw.text((180, 180), emoji, fill="#faa", embedded_color=True, font=fnt)
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
    

    # api.update_profile_image(avatar)
    to_tinybird([{'batch': batch, 'date': str(datetime.now()), 'polarity': polarity, 'hue': hue}], 'polarity_log')


def update_header():
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
        icon = Image.new(mode="RGB", size=(140, 140))
        draw = ImageDraw.Draw(icon)
        draw.text((0, 0), emoji['emoji'], fill="#faa", embedded_color=True, font=fnt)
        out = icon.resize((10, 10))
        rgba = out.convert("RGBA")
        datas = rgba.getdata()
        
        newData = []
        for item in datas:
            if item[0] == 0 and item[1] == 0 and item[2] == 0: 
                newData.append((r2, g2, b2, 0))
            else:
                newData.append(item)
        
        rgba.putdata(newData)
        Image.Image.paste(stripes, rgba, (10*i, int(p['polarity'] * -2.50 + 250)))
        i += 1
    stripes.save(f'{path}/stripes.png')


def run():
    print('here we go again bitch...')
    since_id = get_last_tweet_id(tb_api)
    tweets_raw = get_tweets(since_id)
    tweets = []
    for tweet in tweets_raw:
        tweet = tweet._json
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
            tweets.append({'search_term': batch, 'batch': batch, 'id': tweet['id'], 'date': parsedate_to_datetime(str(tweet['created_at'])).strftime("%Y-%m-%d %H:%M:%S"), 'text': text, 'polarity': enrich_polarity(text), 'tweet': text})
    to_tinybird(tweets, datasource)
    to_tinybird(tweets, 'tweets_s__v0')
    polarity = get_polarity(tb_api)
    if polarity:
        hue = polarity2hue(polarity)
        emoji = get_emoji(tb_api)[0]['emoji']
        update_avatar(hue, polarity, emoji)

    data = get_polarity_mvng_avg(tb_api)
    emojis = get_emoji(tb_api, limit=150)
    create_stripes(data, emojis)
    update_header()
