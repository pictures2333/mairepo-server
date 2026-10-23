import hashlib
import os

def random_filename() -> str:
    return hashlib.sha256(os.urandom(128)).hexdigest()
