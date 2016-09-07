### random_sketches.py
### This is an implementation of a random_sketches_fname -- that return a random file name from my sketches
### directory.

from os import walk
import os
import random

DRAFTS_SKETCHES_PATH = "/home/popolit/drafts/sketches"
ALL_SKETCHES = None
def populate_all_sketches():
    global ALL_SKETCHES
    ALL_SKETCHES = []
    for (dirpath, dirnames, filenames) in walk(DRAFTS_SKETCHES_PATH):
        ALL_SKETCHES.extend(map(lambda x: os.path.join(dirpath, x),
                                filter(lambda x: x[-4:] == ".pdf",
                                       filenames)))
    return True

def random_sketches_fname():
    if not ALL_SKETCHES:
        populate_all_sketches()

    return os.path.join(DRAFTS_SKETCHES_PATH, random.choice(ALL_SKETCHES))


