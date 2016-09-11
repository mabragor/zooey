
import subprocess
import os

def take_zooey_lock():
    code = subprocess.call(["mkdir", os.path.expanduser("~/.zooey_lock")])
    if code == 0:
        return True
    print "Zooey lock is already taken by someone!"
    return False

def release_zooey_lock():
    subprocess.call(["rmdir", os.path.expanduser("~/.zooey_lock")])

def zooey_lock():
    class Frob(object):
        def __enter__(self):
            if not take_zooey_lock():
                raise Exception("Zooey lock is already taken")
            return True
        def __exit__(self, type, value, traceback):
            release_zooey_lock()
            return False
        
    return Frob()
