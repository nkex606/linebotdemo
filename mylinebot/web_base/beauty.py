import yaml
from pymongo import MongoClient

config = None
mongo_host = 'johnchang.linebot.mongo'
mongo_port = 27017


def load_config(path):
    global config
    with open(path, 'r') as f:
        config = yaml.load(f)
    return config


def get_content_images(web):
    return web.get_content_images()


def insert_mongo(images):
    client = MongoClient(mongo_host, mongo_port)
    db = client['images']
    collection = db['beauty']
    images = remove_duplicate(images, collection.find())
    collection.insert_many([{'url': url.replace('http:', 'https')} for url in images])
    client.close()


def remove_duplicate(images, data):
    s1 = images
    s2 = set()
    for d in data:
        s2.add(d['url'])
    return s1 - s2
