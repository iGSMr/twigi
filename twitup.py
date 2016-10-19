#!/usr/bin/env python3

from TwitterAPI import TwitterAPI
import os
import sys
import logging
import libstory
import argparse
from configparser import ConfigParser
import time
from http.server import BaseHTTPRequestHandler,HTTPServer
from http.client import HTTPSConnection
from urllib.parse import urlparse, parse_qs,quote,urljoin
import threading
import json
import io
import tempfile

import requests
import ssl
from pprint import pprint

logging.basicConfig(format='%(asctime)s %(levelname)-10s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',level=logging.DEBUG)

logger = logging.getLogger("twitterstory.main")

VIDEO_FILENAME = 'C:/Users/igi.VIZRTINT/Desktop/Twitter/sample_twitter.mp4'
TWEET_TEXT = 'Cñéóíáénê!'

"""CONSUMER_KEY = 'aNS7nZxb9EOUKLNxJdVBd9bhj'
CONSUMER_SECRET = 'eOfp395xQkQAX2KMcVYHORLj2DrZF31WMnwV0p7ymHQiWolSRi'
ACCESS_TOKEN_KEY = '8102552-r08dIaPKt7PpEpITGL21egnPhjY0pOdWOoj89g19Dg'
ACCESS_TOKEN_SECRET = 'ZbIc1zfOczx1ZaHoO85WyHkny9szyXAfoByVNnhIQqGka'


api = TwitterAPI(CONSUMER_KEY,
                 CONSUMER_SECRET,
                 ACCESS_TOKEN_KEY,
                 ACCESS_TOKEN_SECRET)


bytes_sent = 0
total_bytes = os.path.getsize(VIDEO_FILENAME)
print("Bytes a subir: %s" % total_bytes)
file = open(VIDEO_FILENAME, 'rb')
"""

def check_status(r):
    print(r.status_code)
    print(r.text)
    if r.status_code < 200 or r.status_code > 299:
        print(r.status_code)
        print(r.text)
        sys.exit(0)

"""r = api.request('media/upload',
                {'command': 'INIT',
                 'media_type': 'video/mp4',
                 'total_bytes': total_bytes})
check_status(r)

media_id = r.json()['media_id']
segment_id = 0

while bytes_sent < total_bytes:
    chunk = file.read(4*1024*1024)
    r = api.request('media/upload', {'command': 'APPEND', 'media_id': media_id, 'segment_index': segment_id}, {'media': chunk})
    check_status(r)
    segment_id = segment_id + 1
    bytes_sent = file.tell()
    print('[' + str(total_bytes) + ']', str(bytes_sent))

r = api.request('media/upload', {'command': 'FINALIZE', 'media_id': media_id})
check_status(r)

r = api.request('statuses/update', {'status': TWEET_TEXT, 'media_ids': media_id})
check_status(r)

"""
def main(args):
    target_id = None
    server_url = None
    try:
        target_id = args["storyhub"]["target_id"]
        logger.info("[TwitStory] Target ID: %s " % target_id)
        server_url = args["storyhub"]["url"]
        logger.info("[TwitStory] Server URL: %s " % server_url)
    except KeyError as e:
        logger.error("missing entry in configuration: {}".format(*e.args))
        sys.exit(1)
    """try:
        target=None
        logger.info("Connecting to story server {}".format(server_url))
        s=libstory.StoryHubClient()
        s.connect(server_url)
        target=s.get_output_target(target_id)
        if target == None or update_outputtarget:
            target=libstory.OutputTarget(s)
            try:
                target.title=args["storyhub"]["target_name"]
                target.id=target_id
                target.concept=args["encoding"]["concept"] if "concept" in args["encoding"] else None
                target.variant=args["encoding"]["variant"] if "variant" in args["encoding"] else None
                target.width=args["encoding"]["width"]
                target.height=args["encoding"]["height"]
                target.profile=args["encoding"]["profile"]
                target.extension=args["encoding"]["extension"]
                target.icon=args["storyhub"]["icon"]
            except KeyError as e:
                    logger.error("missing entry in configuration: {}".format(*e.args))
                    sys.exit(1)
            target=s.create_target(target)
        for item in target.unclaimed():
            try:
              item.claim()
            except libstory.UnableToClaimItem as e:
              print("Oooops!")
            publish_to_facebook(s,item,args)
    except libstory.CollectionMissing as e:
        logger.error("Could not find {} in service document. Is this a story hub?".format(e.term))
        sys.exit(3)
    except ConnectionRefusedError as e:
        logger.error("Unable to connect to story server ({1})".format(*e.args))
        sys.exit(2)"""

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("configfile")
        parser.add_argument("-u","--update_outputtarget",dest="update_outputtarget",action="store_true",help="Force updating the outputtarget, even if it already exists")
        args = parser.parse_args()
        main(args)
    except KeyboardInterrupt as e:
        logger.info("Interrupted by user.")
        sys.exit(1)