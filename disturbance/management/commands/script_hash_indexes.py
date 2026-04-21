from django.core.management.base import BaseCommand
from confy import env
import os
from django.conf import settings
import hashlib
import base64
import json

STATIC_APP_NAME = env("STATIC_APP_NAME", "disturbance")
STATIC_DIRECTORY = env("STATIC_DIRECTORY", os.path.join(settings.BASE_DIR, STATIC_APP_NAME, 'static'))
STATIC_FILES_DIRECTORY_NAME = env("STATIC_FILES_DIRECTORY_NAME", "staticfiles_ds")
STATIC_FILES_DIRECTORY = env("STATIC_FILES_DIRECTORY", os.path.join(settings.BASE_DIR, STATIC_FILES_DIRECTORY_NAME))
FILE_TYPES_TO_HASH = env("FILE_TYPES_TO_HASH", [".js",".css", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".woff", ".woff2", ".ttf"])
SRI_FILE_STRUCTURE_DIR = os.path.join(settings.BASE_DIR, "sri-files")

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate and store hash indexes for all static files'

    def file_sha384(self, file_location):
        h = hashlib.sha384()
        with open(file_location, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        digest = h.digest()
        b64 = base64.b64encode(digest).decode("utf-8")
        return f"sha384-{b64}"


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

        static_dir_list = self.get_files(STATIC_DIRECTORY)
        #convert to actual static location
        static_dir_list = list(map(lambda file_location: (file_location, file_location.replace(STATIC_DIRECTORY,'/static')), static_dir_list))
        
        static_files_dir_list = self.get_files(STATIC_FILES_DIRECTORY)
        #convert to actual static location
        static_files_dir_list = list(map(lambda file_location: (file_location, file_location.replace(STATIC_FILES_DIRECTORY,'/static')), static_files_dir_list))

        file_location_list = static_dir_list + static_files_dir_list

        #create hash tuple list
        file_hash_tuple_list = list(map(lambda file_location: (file_location[1], self.file_sha384(file_location[0])), file_location_list))
        
        data = dict(file_hash_tuple_list)

        with open("sri-manifest.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        #TODO determine if filenames should be based on real location or static url

        #clear out existing files        
        for root, _, files in os.walk(SRI_FILE_STRUCTURE_DIR):
            for file in files:
                os.remove(os.path.join(root, file))

        #replace file location in list with hash of name
        file_name_file_hash_tuple_list = list(map(lambda file_hash_tuple: (hashlib.sha256(file_hash_tuple[0].encode()).hexdigest(),file_hash_tuple[1]), file_hash_tuple_list))
        #iterate through lists, create dir based on first two chars of each file name hash
        file_structure_directories = list(set(list(map(lambda file_name_file_hash_tuple: file_name_file_hash_tuple[0][:2], file_name_file_hash_tuple_list))))

        #create directories
        for dir in file_structure_directories:
            os.makedirs(os.path.join(SRI_FILE_STRUCTURE_DIR, dir), exist_ok=True)

        #create files at locations 
        for file_name_file_hash_tuple in file_name_file_hash_tuple_list:
            location = os.path.join(SRI_FILE_STRUCTURE_DIR, file_name_file_hash_tuple[0][:2], file_name_file_hash_tuple[0])
            data = file_name_file_hash_tuple[1]
            with open(location, "w") as f:
                f.write(data)