
import mysql.connector
import subprocess
import os
import getpass

### ZOOEY lock
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

### Connections to MySQL using zooey user

def get_mysql_zooey_connection(login, passwd):
    return mysql.connector.connect(user=login,
                                   password=passwd,
                                   host='127.0.0.1',
                                   database='zooey')


def interactive_get_mysql_zooey_connection():
    print "Enter MySQL credentials of zooey user"
    
    zooey_login = raw_input("Login (default: zooey)> ")
    if zooey_login == '':
        zooey_login = 'zooey'
    zooey_passwd = getpass.getpass("Password> ")
    print ''
    return get_mysql_zooey_connection(zooey_login, zooey_passwd)

def mysql_zooey_connection(login, passwd):
    class Frob(object):
        def __enter__(self):
            self.conn = get_mysql_zooey_connection(login, passwd)
            return self.conn
        def __exit__(self, type, value, traceback):
            self.conn.disconnect()
            return False

    return Frob()
