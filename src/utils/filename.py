from hashlib import sha256
import os

def filename() -> str:
    return sha256(os.urandom(128)).hexdigest()
