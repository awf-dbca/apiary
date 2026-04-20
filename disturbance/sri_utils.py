import hashlib
from django.conf import settings
import os

import logging
logger = logging.getLogger(__name__)

SRI_FILE_STRUCTURE_DIR = os.path.join(settings.BASE_DIR, "sri-files")

#draft script for hash check util

def lookup_hash(filename):

    if not filename:
        logger.error("No filename provided for hash lookup.")

    hashed_filename = hashlib.sha256(filename.encode()).hexdigest()
    hashed_dir = hashed_filename[:2]

    check_file_path = os.path.join(SRI_FILE_STRUCTURE_DIR, hashed_dir, hashed_filename)
    
    with open(check_file_path, "r") as f:
        hash = f.readline()

    return hash