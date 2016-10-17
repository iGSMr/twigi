from TwitterAPI import TwitterAPI
import os
import sys


VIDEO_FILENAME = 'C:/Users/igi.VIZRTINT/Desktop/test.mp4'
TWEET_TEXT = 'Video upload test'

CONSUMER_KEY = 'aNS7nZxb9EOUKLNxJdVBd9bhj'
CONSUMER_SECRET = 'eOfp395xQkQAX2KMcVYHORLj2DrZF31WMnwV0p7ymHQiWolSRi'
ACCESS_TOKEN_KEY = '8102552-r08dIaPKt7PpEpITGL21egnPhjY0pOdWOoj89g19Dg'
ACCESS_TOKEN_SECRET = 'ZbIc1zfOczx1ZaHoO85WyHkny9szyXAfoByVNnhIQqGka'

def check_status(r):
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
#r = api.request('statuses/update', {'status': 'Que pasa? Atleti!'})
#print 'SUCCESS' if r.status_code == 200 else 'FAILURE'

# STEP 1 - upload image
file = open('C:/Users/igi.VIZRTINT/Desktop/probando.png', 'rb')
data = file.read()
r = api.request('media/upload', None, {'media': data})
print('UPLOAD MEDIA SUCCESS' if r.status_code == 200 else 'UPLOAD MEDIA FAILURE')

# STEP 2 - post tweet with reference to uploaded image
if r.status_code == 200:
        media_id = r.json()['media_id']
        r = api.request('statuses/update', {'status': 'Testing, probando me lees?', 'media_ids':media_id})
        print('UPDATE STATUS SUCCESS' if r.status_code == 200 else 'UPDATE STATUS FAILURE')

check_status(r)
