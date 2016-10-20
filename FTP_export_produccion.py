#!/usr/bin/env python3

import logging

logging.basicConfig(format='%(asctime)s %(levelname)-10s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
import argparse
import libstory
from urllib.parse import urlparse
from tempfile import TemporaryFile
import os.path
from configparser import ConfigParser

logger = logging.getLogger("traza")


def sane_filename(filename, subschar):
    out = ""
    previous_sub = None
    for i, char in enumerate(filename):
        if (char in '"<>:/\\|?*') or (ord(char) <= 31):
            if not previous_sub:
                out += subschar
            previous_sub = True
        else:
            out += char
            previous_sub = False
    return out


class PayloadWriter:
    def __init__(self, item):
        self.item = item

    def write(self, fp):
        fp.write(self.item.get_metadata().xml())


# FILENAME_PATTERN="br_ite_oi2_{title}_{timestamp:%Y-%m-%dT%H.%M.%S}"
FILENAME_PATTERN = "{title}_{timestamp:%Y-%m-%dT%H.%M.%S}"
logger.info("VALOR DEL TITLE: %s" % FILENAME_PATTERN)


class FileSystemExportAgent(libstory.BasePublishingAgent):
    def create_filename(self, item, extension):
        payload = item.get_metadata()
        filename_args = {}
        for k in payload:
            filename_args[k] = payload[k]
        filename_args["timestamp"] = item.timestamp
        name = FILENAME_PATTERN.format(**filename_args)
        logger.info("VALOR DEL name: %s" % name)
        return sane_filename(name, "_") + extension

    def open_outfile(self, item, extension="", temp=False):
        if (temp):
            return TemporaryFile(suffix=extension)
        else:
            path = self.config["exportfolder"]["path"]
            return open(os.path.join(path, self.create_filename(item, extension)), "wb")

    def download(self, item, writer, ext, ftpclient=None):
        with self.open_outfile(item, ext, ftpclient is not None) as out:
            writer(out)
            if (ftpclient is not None):
                out.seek(0)
                path = urlparse(self.config["exportfolder"]["path"]).path
                logger.info("VALOR DE item : %s" % item)
                logger.info("VALOR de EXT: %s" % ext)
                logger.info("VALOR de path: %s" % path)

                #filepath = os.path.join(path, self.create_filename(item, ext))
                logger.info("VALOR del FILEPATH1 antes formateo: %s" % filepath)
                ftpclient.storbinary("STOR {}".format(filepath), out)
                logger.info("VALOR del FILEPATH2 despues formateo: %s" % format(filepath))

    def deliver_item(self, item):
        progress = item.get_progress()
        progress.status = "PENDING"
        progress.status_description = "Saving story to disk"
        progress.progress = 1
        progress.total_progress = 3
        self.hub.update_progress(progress)

        ftpclient = None
        output_location = self.config["exportfolder"]["path"]
        logger.info("VALOR DEL output_location: %s" % output_location)
        if (output_location.startswith("ftp://")):
            ftpclient = libstory.FtpClient(output_location)
            logger.info("VALOR DEL ftp CLIENT: %s" % ftpclient)
        self.download(item, PayloadWriter(item).write, ".xml", ftpclient=ftpclient)

        progress.progress = 2
        self.hub.update_progress(progress)
        self.download(item, item.download_media, self.config["encoding"]["extension"], ftpclient=ftpclient)
        progress.progress = 3
        progress.status = "COMPLETED"
        self.hub.update_progress(progress)
        progress.step = "PUBLISHED"
        self.hub.update_progress(progress)


if __name__ == "__main__":
    import sys

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("configfile")
        parser.add_argument("-u", "--update_outputtarget", dest="update_outputtarget", action="store_true",
                            help="Force updating the outputtarget, even if it already exists")
        args = parser.parse_args()
        config = ConfigParser()
        config.read(args.configfile)
        agent = FileSystemExportAgent(config)
        if args.update_outputtarget:
            agent.connect()
            agent.update_output_target()
        agent.run()

    except KeyboardInterrupt as e:
        logger.info("Interrupted by user.")