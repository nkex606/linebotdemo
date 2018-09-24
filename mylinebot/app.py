# -*- coding: utf-8 -*-

import os
import sys
import random
import logging
import geoip2.database
import googlemaps
from pymongo import MongoClient
from geoip2.errors import AddressNotFoundError
from logging.handlers import RotatingFileHandler

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, LocationMessage, ImageSendMessage
)
from web_base import beauty
from web_base.web import Web
from my_nltk.my_chat import get_bot


app = Flask(__name__)
app.debug = True

# logger
log_handler = RotatingFileHandler('bot.log', maxBytes=10000, backupCount=1)
log_handler.setLevel(logging.INFO)
app.logger.addHandler(log_handler)

# geoip reader
reader = geoip2.database.Reader(os.path.join(os.getcwd(), 'GeoLite2-City.mmdb'))

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
gmap_key = os.getenv('GMAP_API_KEY', None)

if channel_secret is None:
    app.logger.error('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    app.logger.error('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if gmap_key is None:
    app.logger.error('Specify GMAP_API_KEY as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# get a bot instance
my_bot = get_bot()


@app.route('/callback', methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info('Request body: ' + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    if event.message.text == u'\u62bd':
        body = query_db()
        app.logger.info('body: {}'.format(body))
        image_url = body['url']

        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
        )
    else:
        resp = my_bot.respond(event.message.text)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=resp)
        )


@handler.add(MessageEvent, message=LocationMessage)
def message_location(event):
    lat = event.message.latitude
    lng = event.message.longitude

    if event.source.type == 'user':
        target_id = event.source.user_id
    elif event.source.type == 'group':
        target_id = event.source.group_id
    else:
        target_id = event.source.room_id

    query_results = gmap_search_nearby(lat, lng)
    for result in query_results:
        if 'opening_hours' in result:
            if result['opening_hours']['open_now']:
                line_bot_api.push_message(target_id, TextSendMessage(text=result['name'] + '\n' + result['vicinity']))


def gmap_search_nearby(lat, lng):
    """
    Use google map api to search nearby restaurants by the given location, default keyword is restaurants,
    the radius parameter should not be used cause we indicate `rankby` parameter
    :param lat: location latitude
    :param lng: location longitude
    :return: list of restaurants
    """
    gmaps = googlemaps.Client(key=gmap_key)
    query_result = gmaps.places_nearby(location=(lat, lng), rank_by='distance', keyword='restaurants')
    return query_result['results']


def get_geoip(ip):
    try:
        response = reader.city(ip)
    except AddressNotFoundError:
        app.logger.error('Source ip address: {} is not found in database.'.format(ip))
        return None
    return response


def query_db():
    client = MongoClient('johnchang.linebot.mongo', 27017)
    db = client['images']
    collection = db['beauty']
    count = collection.count()
    if count == 0:
        config = beauty.load_config(os.path.join(os.path.dirname(__file__), 'web_base/config.yaml'))
        site = config['site']['name']
        url = config['site']['url']
        content_tag = config['site']['html_tag']['content']['name']
        content_clazz = config['site']['html_tag']['content']['clazz']
        image_tag = config['site']['html_tag']['img']['name']
        image_clazz = config['site']['html_tag']['img']['clazz']
        web = Web(site, url, content_tag, content_clazz, image_tag, image_clazz)
        images = beauty.get_content_images(web)
        beauty.insert_mongo(images)
    return collection.find()[random.randrange(count)]
