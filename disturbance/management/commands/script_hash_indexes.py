from django.core.management.base import BaseCommand
from confy import env
import os
from django.conf import settings
import hashlib
import base64

STATIC_APP_NAME = env("STATIC_APP_NAME", "disturbance")
STATIC_DIRECTORY = env("STATIC_DIRECTORY", os.path.join(os.path.join(settings.BASE_DIR, STATIC_APP_NAME, 'static')))
STATIC_FILES_DIRECTORY_NAME = env("STATIC_FILES_DIRECTORY_NAME", "staticfiles_ds")
STATIC_FILES_DIRECTORY = env("STATIC_FILES_DIRECTORY", os.path.join(os.path.join(settings.BASE_DIR, STATIC_FILES_DIRECTORY_NAME)))
FILE_TYPES_TO_HASH = env("FILE_TYPES_TO_HASH", [".js",".css", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".woff", ".woff2", ".ttf"])

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate and store hash indexes for all static files'

    def file_sha256(self, file_location):
        h = hashlib.sha256()
        with open(file_location, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        digest = h.digest()
        b64 = base64.b64encode(digest).decode("utf-8")
        return f"sha256-{b64}"


    def get_files(self, directory):
        file_location_list = []
        #get all files/dirs in provided directory
        items = [os.path.join(directory, e) for e in os.listdir(directory)]

        files = [p for p in items if os.path.isfile(p) and os.path.splitext(p)[1] in FILE_TYPES_TO_HASH]
        dirs  = [p for p in items if os.path.isdir(p)]

        #add files to location list
        file_location_list += files

        #add dir files to location list
        for dir in dirs:
            file_location_list += self.get_files(dir)

        return file_location_list

    def handle(self, *args, **options):
        print(FILE_TYPES_TO_HASH)
        #check STATIC_APP_NAME
        if not STATIC_APP_NAME:
            logger.error("STATIC_APP_NAME not provided.")

        #validate static dir
        if not (os.path.isdir(STATIC_DIRECTORY)):
            logger.error("Provided STATIC_DIRECTORY not valid.")

        if not (os.path.isdir(STATIC_FILES_DIRECTORY)):
            logger.error("Provided STATIC_FILES_DIRECTORY not valid.")

        file_location_list = []
        file_location_list += self.get_files(STATIC_DIRECTORY)
        file_location_list += self.get_files(STATIC_FILES_DIRECTORY)

        #create hash tuple list
        file_hash_tuple_list = list(map(lambda file_location: (file_location, self.file_sha256(file_location)), file_location_list))

        for i in file_hash_tuple_list:
            print(i)

        print(len(file_hash_tuple_list))