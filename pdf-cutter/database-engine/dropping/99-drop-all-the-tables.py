#!/usr/bin/python2

from __future__ import with_statement

import readline
import getpass

import mysql.connector
import sys
import time

from utils import zooey_lock, interactive_get_mysql_zooey_connection

READLINE_CONFIG = '''
set bell-style none
set disable-completion on
'''

ZOOEY_DB_NAME = 'zooey'

for line in READLINE_CONFIG.split("\n"):
    # print line
    readline.parse_and_bind(line)

def drop_cameras_table(conn):
    conn.cursor().execute('drop table if exists cameras')
    print "Cameras table dropped"

def drop_worlds_table(conn):
    conn.cursor().execute('drop table if exists worlds')
    print "Worlds table dropped"

def drop_boxes_table(conn):
    conn.cursor().execute('drop table if exists boxes')
    print "Boxes table dropped"

def drop_under_objects_table(conn):
    conn.cursor().execute('drop table if exists under_objects')
    print "Under objects table dropped"

def drop_lock_table(conn):
    conn.cursor().execute('drop table if exists lock')
    print "Lock table dropped"

def prompt_for_right_phrase(msg, phrase):
    print msg
    ans = raw_input("Please enter '%s' if you really want to continue: " % phrase)
    while True:
        if ans == phrase:
            return True
        ans = raw_input("Phrase doesn't match -- try again or, perhaps, you want to Ctrl+D to interrupt?: ")

    return False
        
if __name__ == '__main__':
    with zooey_lock():
        print "*********************************************"
        print "** Welcome to zooey table-dropping script. **"
        print "*********************************************"

        if not prompt_for_right_phrase("You are about to irreversibly drop all zooey tables.",
                                       "drop-all-zooey-tables"):
            exit()
        
        conn = interactive_get_mysql_zooey_connection()
        print "Successfully got a connection!"

        print "Final countdown (use Ctrl+D to interrupt)"
        for i in xrange(10, 0, -1):
            print i
            time.sleep(1)
        
        drop_cameras_table(conn)
        drop_worlds_table(conn)
        drop_boxes_table(conn)
        drop_under_objects_table(conn)
    
        conn.close()
    
