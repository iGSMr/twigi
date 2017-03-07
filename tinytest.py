from TwitterAPI import TwitterAPI
import os
import sys
import time
import requests
from requests_oauthlib import OAuth1

VIDEO_FILENAME = 'C:/Users/igi.VIZRTINT/Desktop/Twitter/long.mp4'
TWEET_TEXT = 'Video upload test'

CONSUMER_KEY = 'aNS****9bhj'
CONSUMER_SECRET = 'eOfp****WolSRi'
ACCESS_TOKEN = '810***19Dg'
ACCESS_TOKEN_SECRET = 'ZbI***qGka'

"""def check_status(r):
    print(r.status_code)
    print(r.text)
    if r.status_code < 200 or r.status_code > 299:
        print(r.status_code)
        print(r.text)
        sys.exit(0)


api = TwitterAPI(CONSUMER_KEY,
                 CONSUMER_SECRET,
                 ACCESS_TOKEN_KEY,
                 ACCESS_TOKEN_SECRET)


bytes_sent = 0
total_bytes = os.path.getsize(VIDEO_FILENAME)
print("Bytes a subir: %s" % total_bytes)
file = open(VIDEO_FILENAME, 'rb')

r = api.request('media/upload',
                {'command': 'INIT',
                 'media_type': 'video/mp4',
                 'total_bytes': total_bytes})
check_status(r)

media_id = r.json()['media_id']
segment_id = 0

while bytes_sent < total_bytes:
    print("Bytes enviados: %s" % bytes_sent)
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

api = TwitterAPI(CONSUMER_KEY,
                 CONSUMER_SECRET,
                 ACCESS_TOKEN_KEY,
                 ACCESS_TOKEN_SECRET)
#r = api.request('statuses/update', {'status': 'Que pasa? Atleti!'})
#print 'SUCCESS' if r.status_code == 200 else 'FAILURE'

# STEP 1 - upload image
file = open('C:/Users/igi.VIZRTINT/Desktop/Twitter/probando.png', 'rb')
data = file.read()
r = api.request('media/upload', None, {'media': data})
print('UPLOAD MEDIA SUCCESS' if r.status_code == 200 else 'UPLOAD MEDIA FAILURE')

# STEP 2 - post tweet with reference to uploaded image
if r.status_code == 200:
        media_id = r.json()['media_id']
        r = api.request('statuses/update', {'status': 'Testing, probando me lees?', 'media_ids':media_id})
        print('UPDATE STATUS SUCCESS' if r.status_code == 200 else 'UPDATE STATUS FAILURE')

check_status(r)
"""

import json
import requests
from requests_oauthlib import OAuth1

MEDIA_ENDPOINT_URL = 'https://upload.twitter.com/1.1/media/upload.json'
POST_TWEET_URL = 'https://api.twitter.com/1.1/statuses/update.json'

oauth = OAuth1(CONSUMER_KEY,
               client_secret=CONSUMER_SECRET,
               resource_owner_key=ACCESS_TOKEN,
               resource_owner_secret=ACCESS_TOKEN_SECRET)


class VideoTweet(object):
    def __init__(self, file_name):
        '''
        Defines video tweet properties
        '''
        self.video_filename = file_name
        self.total_bytes = os.path.getsize(self.video_filename)
        self.media_id = None
        self.processing_info = None

    def upload_init(self):
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

    def upload_append(self):
        '''
        Uploads media in chunks and appends to chunks uploaded
        '''
        segment_id = 0
        bytes_sent = 0
        file = open(self.video_filename, 'rb')

        while bytes_sent < self.total_bytes:
            chunk = file.read(4 * 1024 * 1024)

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
            bytes_sent = file.tell()

            print('%s of %s bytes uploaded' % (str(bytes_sent), str(self.total_bytes)))

        print('Upload chunks complete.')

    def upload_finalize(self):
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
        self.check_status()

    def check_status(self):
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
        self.check_status()

    def tweet(self):
        '''
        Publishes Tweet with attached video
        '''
        request_data = {
            'status': '',
            'media_ids': self.media_id
        }

        req = requests.post(url=POST_TWEET_URL, data=request_data, auth=oauth)
        print(req.json())


if __name__ == '__main__':
    videoTweet = VideoTweet(VIDEO_FILENAME)
    videoTweet.upload_init()
    videoTweet.upload_append()
    videoTweet.upload_finalize()
    videoTweet.tweet()
