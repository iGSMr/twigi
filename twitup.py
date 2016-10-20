#!/usr/bin/env python3

from TwitterAPI import TwitterAPI
import os
import sys
import logging
import libstory
import argparse
from configparser import ConfigParser
import time
import json
import tempfile

from requests_oauthlib import OAuth1
import requests

MEDIA_ENDPOINT_URL = 'https://upload.twitter.com/1.1/media/upload.json'
POST_TWEET_URL = 'https://api.twitter.com/1.1/statuses/update.json'

logging.basicConfig(format='%(asctime)s %(levelname)-10s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',level=logging.DEBUG)
logger = logging.getLogger("twitterstory.main")

"""
Class TweetVideo
"""
class VideoTweet(object):
    def __init__(self, file_name, size):
        '''
        Defines video tweet properties
        '''
        self.video_filename = file_name
        self.total_bytes = size
        self.media_id = None
        self.processing_info = None

    def upload_init(self, oauth):
        '''
        Initializes Upload
        '''
        print('INIT')

        request_data = {
            'command': 'INIT',
            'media_type': 'video/mp4',
            'total_bytes': self.total_bytes,
            'media_category': 'tweetvideo'
        }

        req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, auth=oauth)
        media_id = req.json()['media_id']

        self.media_id = media_id

        print('Media ID: %s' % str(media_id))

    def upload_append(self, tmp, oauth):
        '''
        Uploads media in chunks and appends to chunks uploaded
        '''
        segment_id = 0
        bytes_sent = 0
        #file = open(self.video_filename, 'rb')

        while bytes_sent < self.total_bytes:
            chunk = tmp.read(4 * 1024 * 1024)

            print('APPEND')

            request_data = {
                'command': 'APPEND',
                'media_id': self.media_id,
                'segment_index': segment_id
            }

            files = {
                'media': chunk
            }

            req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, files=files, auth=oauth)

            if req.status_code < 200 or req.status_code > 299:
                print(req.status_code)
                print(req.text)
                sys.exit(0)

            segment_id = segment_id + 1
            bytes_sent = tmp.tell()

            print('%s of %s bytes uploaded' % (str(bytes_sent), str(self.total_bytes)))

        print('Upload chunks complete.')

    def upload_finalize(self, oauth):
        '''
        Finalizes uploads and starts video processing
        '''
        print('FINALIZE')

        request_data = {
            'command': 'FINALIZE',
            'media_id': self.media_id
        }

        req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, auth=oauth)
        print(req.json())

        self.processing_info = req.json().get('processing_info', None)
        self.check_status(oauth)

    def check_status(self, oauth):
        '''
        Checks video processing status
        '''
        if self.processing_info is None:
            return

        state = self.processing_info['state']

        print('Media processing status is %s ' % state)

        if state == u'succeeded':
            return

        if state == u'failed':
            sys.exit(0)

        check_after_secs = self.processing_info['check_after_secs']

        print('Checking after %s seconds' % str(check_after_secs))
        time.sleep(check_after_secs)

        print('STATUS')

        request_params = {
            'command': 'STATUS',
            'media_id': self.media_id
        }

        req = requests.get(url=MEDIA_ENDPOINT_URL, params=request_params, auth=oauth)

        self.processing_info = req.json().get('processing_info', None)
        self.check_status(oauth)

    def tweet(self, oauth, status):
        '''
        Publishes Tweet with attached video
        '''
        request_data = {
            'status': status,
            'media_ids': self.media_id
        }

        req = requests.post(url=POST_TWEET_URL, data=request_data, auth=oauth)
        print(req.json())


def check_status(r):
    if r.status_code < 200 or r.status_code > 299:
        print(r.status_code)
        print(r.text)
        sys.exit(0)


def tw_publish_video(item, metadata, args, size):

    tw_consumer_key = args["twitter"]["CONSUMER_KEY"]
    tw_consumer_secret = args["twitter"]["CONSUMER_SECRET"]
    tw_access_token_key = args["twitter"]["ACCESS_TOKEN_KEY"]
    tw_access_token_secret = args["twitter"]["ACCESS_TOKEN_SECRET"]
    api = OAuth1(client_key=tw_consumer_key,
                 client_secret=tw_consumer_secret,
                 resource_owner_key=tw_access_token_key,
                 resource_owner_secret=tw_access_token_secret)
    try:
        with tempfile.NamedTemporaryFile(suffix=config["encoding"]["extension"]) as tmp:
            item.download_media(tmp)
            size = tmp.tell()
            logger.info("Size of file: %s " % size)
            tmp.seek(0)
            videotweet = VideoTweet(item, size)
            videotweet.upload_init(api)
            videotweet.upload_append(tmp, api)
            videotweet.upload_finalize(api)
            status = metadata["title"] + "||" + metadata ["description"]
            videotweet.tweet(api, status)
    except requests.exceptions.HTTPError as e:
        resp=json.loads(e.response.content.decode("UTF-8"))
        print(resp)

    """
    r = api.request('media/upload',
                    {'command': 'INIT',
                     'media_type': 'video/mp4',
                     'total_bytes': metadata["file_size"]})
    check_status(r)

    media_id = r.json()['media_id']

    segment_id = 0
    bytes_sent = 0

    while bytes_sent < metadata["file_size"]:
        chunk = filepointer.file.read(4 * 1024 * 1024)
        r = api.request('media/upload', {'command': 'APPEND', 'media_id': media_id, 'segment_index': segment_id},
                        {'media': chunk})
        check_status(r)
        segment_id = segment_id + 1
        bytes_sent = filepointer.file.tell()
        print('[' + str(size) + ']', str(bytes_sent))

    r = api.request('media/upload', {'command': 'FINALIZE', 'media_id': media_id})
    check_status(r)

    r = api.request('statuses/update', {'status': metadata["description"], 'media_ids': media_id})
    check_status(r)
    """


def publish_to_twitter(hub, item, config):
    progress = item.get_progress()
    progress.status = "PENDING"
    progress.step = "CLAIMED"
    progress.status_description = "Publishing to Twitter"
    progress.progress = 1
    progress.total_progress = 5
    hub.update_progress(progress)
    payload = item.get_metadata()
    progress.progress = 2
    hub.update_progress(progress)
    try:
        with tempfile.NamedTemporaryFile(suffix=config["encoding"]["extension"]) as tmp:
            item.download_media(tmp)
            progress.progress=3
            hub.update_progress(progress)
            size = tmp.tell()
            logger.info("Size of file: %s " % size)
            tmp.seek(0)
            progress.progress=4
            hub.update_progress(progress)
            tw_metadata = {"title": payload["title"], "description": payload["description"], "file_size": size}
            tw_publish_video(item,tw_metadata,config, size)
        # file should now be gone!
        progress.progress=5
        progress.status="COMPLETED"
        progress.step="PUBLISHED"
        hub.update_progress(progress)
    except requests.exceptions.HTTPError as e:
        progress.status="ERROR"
        resp=json.loads(e.response.content.decode("UTF-8"))
        progress.status_description=resp["error"]["message"]
        hub.update_progress(progress)


def main(args):
    target_id = None
    server_url = None
    try:
        tw_consumer_key = args["twitter"]["CONSUMER_KEY"]
        tw_consumer_secret = args["twitter"]["CONSUMER_SECRET"]
        tw_access_token_key = args["twitter"]["ACCESS_TOKEN_KEY"]
        tw_access_token_secret = args["twitter"]["ACCESS_TOKEN_SECRET"]
        target_id = args["storyhub"]["target_id"]
        server_url = args["storyhub"]["url"]
        logger.info("[TwitStory] Target ID: %s " % target_id)
        logger.info("[TwitStory] Server URL: %s " % server_url)
        logger.info("[TwitStory] Consumer key: %s " % tw_consumer_key)
        logger.info("[TwitStory] Consumer secret: %s " % tw_consumer_secret)
        logger.info("[TwitStory] Access Token key: %s " % tw_access_token_key)
        logger.info("[TwitStory] Access Token secret: %s " % tw_access_token_secret)

    except KeyError as e:
        logger.error("missing entry in configuration: {}".format(*e.args))
        sys.exit(1)
    try:
        target = None
        logger.info("Connecting to story server {}".format(server_url))
        s = libstory.StoryHubClient()
        s.connect(server_url)
        target = s.get_output_target(target_id)
        if target is None:
            target = libstory.OutputTarget(s)
            try:
                target.title = args["storyhub"]["target_name"]
                target.id = target_id
                target.concept = args["encoding"]["concept"] if "concept" in args["encoding"] else None
                target.variant = args["encoding"]["variant"] if "variant" in args["encoding"] else None
                target.width = args["encoding"]["width"]
                target.height = args["encoding"]["height"]
                target.profile = args["encoding"]["profile"]
                target.extension = args["encoding"]["extension"]
                target.icon = args["storyhub"]["icon"]
            except KeyError as e:
                    logger.error("missing entry in configuration: {}".format(*e.args))
                    sys.exit(1)
            target = s.create_target(target)
        for item in target.unclaimed():
            try:
              item.claim()
            except libstory.UnableToClaimItem as e:
              print("Oooops!")
            publish_to_twitter(s, item, args)
    except libstory.CollectionMissing as e:
        logger.error("Could not find {} in service document. Is this a story hub?".format(e.term))
        sys.exit(3)
    except ConnectionRefusedError as e:
        logger.error("Unable to connect to story server ({1})".format(*e.args))
        sys.exit(2)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("configfile")
        parser.add_argument("-u", "--update_outputtarget", dest="update_outputtarget", action="store_true", help="Force updating the outputtarget, even if it already exists")
        args = parser.parse_args()
        config = ConfigParser()
        config.read(args.configfile)
        main(config)

    except KeyboardInterrupt as e:
        logger.info("Interrupted by user.")
        sys.exit(1)


