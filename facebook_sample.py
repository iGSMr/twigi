#!/usr/bin/env python3

import logging
import libstory
import argparse
from configparser import ConfigParser
import sys
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

logger = logging.getLogger("facebookstory.main")


class NoPageAccessException(Exception):
  pass


class InvalidTokenException(Exception):
    pass


class SessionExpiredException(InvalidTokenException):
    pass


class GetHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        message="Resource not found".encode("UTF-8")
        parsed_path = urlparse(self.path)
        done=False
        response=404
        if parsed_path.path == "/login_success.html":
            message="""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Redirecting...</title>
            <script>
            window.location="/go?"+window.location.hash.substring(1)
            </script>
            </head><body></body></html>""".encode("UTF-8")
            response=200
        elif parsed_path.path=="/go":
            self.server.access_token=parse_qs(parsed_path.query)["access_token"][0]
            print("Access token: {}".format(self.server.access_token))
            message= "Thank you, access token will be stored to the config file, and the publishing script will now continue".encode("UTF-8")
            done=True
            response=200
        print(message)
        self.send_response(response)
        self.end_headers()
        self.wfile.write(message)
        serverController=ServerShutdown(self.server)
        logger.info("Got user token. Stopping receiver...")
        serverController.start()
        return


class ServerShutdown(threading.Thread):
    def __init__(self,server):
        self.server=server
        threading.Thread.__init__(self)
    def run(self):
        time.sleep(2)
        self.server.shutdown()
        logger.info("Token receiver stopped")


def read_fb_response(sresponse):
    response=json.loads(sresponse)
    if "error" in response:
        if response["error"]["code"] == 190:
            if response["error"]["error_subcode"] == 463:
                raise SessionExpiredException()
            raise InvalidTokenException()
    return response


def fb_get_page_token(pageid,user_token,insecure=False):

    context=None
    if insecure:
        context=ssl._create_unverified_context()
    conn=HTTPSConnection("graph.facebook.com:443",context=context)
    conn.request("GET","/me/accounts?access_token={}".format(user_token))
    res=conn.getresponse()
    acc=read_fb_response(res.read().decode("UTF-8"))
    pprint(acc)
    pages=",".join(['{} ({})'.format(e["name"],e["id"]) for e in acc["data"]])
    logger.info("User has access to {}".format(pages))
    try:
      return [e["access_token"] for e in acc["data"] if e["id"] == pageid][0]
    except IndexError as e:
      raise NoPageAccessException("User don't have access to any page with the specified id ({})".format(pageid))


def fb_publish_video(pageid, access_token, filepointer, metadata, insecure=False):
    if access_token:
        metadata["access_token"] = access_token
    verify = False if insecure else True
    res = requests.post("https://graph-video.facebook.com/v2.6/{page_id}/videos".format(page_id=pageid),data=metadata,files={"source":filepointer},verify=verify)
    print(res.content)
    print(res.status_code)
    res.raise_for_status()

def publish_to_facebook(hub, item, config):
    progress = item.get_progress()
    progress.status="PENDING"
    progress.step="CLAIMED"
    progress.status_description="Publishing to Facebook"
    progress.progress=1
    progress.total_progress=5
    hub.update_progress(progress)
    payload=item.get_metadata()
    progress.progress=2
    hub.update_progress(progress)
    insecure=allow_unverified(config)

    try:
        with tempfile.NamedTemporaryFile(suffix=config["encoding"]["extension"]) as tmp:
            item.download_media(tmp)
            progress.progress=3
            hub.update_progress(progress)
            size=tmp.tell()
            tmp.seek(0)
            progress.progress=4
            hub.update_progress(progress)
            fb_metadata={"title":payload["title"],"description":payload["description"],"file_size":size}
            fb_publish_video(config["facebook"]["page_id"],config["facebook"]["page_token"],tmp,fb_metadata,insecure=insecure)
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


def main(args,update_outputtarget=False):
    target_id=None
    server_url=None
    try:
        target_id=args["storyhub"]["target_id"]
        server_url=args["storyhub"]["url"]
    except KeyError as e:
        logger.error("missing entry in configuration: {}".format(*e.args))
        sys.exit(1)
    try:
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
        sys.exit(2)


def get_facebook_apikey(config):
    print("""In order to publish videos to facebook, we need an access token that
    allows us to publish to your page.
    Please open the following link, and go through the authentication process.
    Once completed, this script will continue.""")

    redirecturi=quote(urljoin("http://"+config["callback_host"],"login_success.html"))

    print("https://www.facebook.com/dialog/oauth?client_id={appid}&redirect_uri={redirecturi}&response_type=token&scope=manage_pages,publish_pages"
        .format(appid=config["appid"],redirecturi=redirecturi))

    server = HTTPServer(('localhost', 9372), GetHandler)

    GetHandler.server=server

    print('Starting server, use <Ctrl-C> to stop')
    server.serve_forever()
    return server.access_token

def allow_unverified(config):
    if "disable ssl certificate validation" in config["facebook"]:
        if config["facebook"]["disable ssl certificate validation"].lower() in ["true","yes"]:
            logger.info("Allowing unverified connections to facebook")
            return True
    return False

"""
   AQUI ES DONDE REALMENTE LOS ARGUMENTOS SE TOMAN Y SE INICIA EL MAIN!!!!
"""
def fb_wrapper(config,args):
    facebook_user_token=None
    try:
        facebook_user_token=config["facebook"]["user_token"]
    except KeyError:
        facebook_user_token = None
    if not facebook_user_token:
        config["facebook"]["user_token"]=get_facebook_apikey(config["facebook"])
        facebook_user_token=config.get("facebook","user_token")
        config.write(open(args.configfile,"w"))

    insecure=allow_unverified(config)

    try:
        config["facebook"]["page_token"]=fb_get_page_token(config["facebook"]["page_id"],config["facebook"]["user_token"],insecure=insecure)
    except NoPageAccessException as e:
        logger.error(e)
        sys.exit(12)


    main(config,update_outputtarget=args.update_outputtarget)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("configfile")
        parser.add_argument("-u","--update_outputtarget",dest="update_outputtarget",action="store_true",help="Force updating the outputtarget, even if it already exists")

        args=parser.parse_args()
        config=ConfigParser()
        config.read(args.configfile)
        retry=True
        while retry:
            try:
                fb_wrapper(config,args)
                retry=False
            except SessionExpiredException as e:
                del config["facebook"]["user_token"]
        config.write(open(args.configfile,"w"))

    except KeyboardInterrupt as e:
        logger.info("Interrupted by user.")
        sys.exit(1)
