#!/usr/bin/python2

from __future__ import with_statement

import readline
import getpass

import mysql.connector
import sys

READLINE_CONFIG = '''
set bell-style none
set disable-completion on
'''

ZOOEY_DB_NAME = 'zooey'

for line in READLINE_CONFIG.split("\n"):
    print line
    readline.parse_and_bind(line)

def zooey_db_exists_p(conn):
    cur = conn.cursor()
    query = ("show databases like '%s'" % ZOOEY_DB_NAME)
    cur.execute(query)
    return len(list(cur)) != 0

def get_y_or_n_answer(initial_prompt, repeat_prompt, default_ans='n'):
    y = 'Y' if default_ans == 'y' else 'y'
    n = 'N' if default_ans == 'n' else 'n'
    ans = raw_input(initial_prompt + ' (%s/%s) ' % (y, n))
    while True:
        if ans == '':
            ans = default_ans
        if (ans.lower() == 'n'):
            return False
        elif (ans.lower() == 'y'):
            return True
        else:
            ans = raw_input(("Sorry, I only understand '%s' or '%s' answers.  " % (y, n))
                            + repeat_prompt)

def create_zooey_db(conn):
    cur = conn.cursor()
    query = 'create database if not exists zooey'
    cur.execute(query)

def ok_or_fail_print(msg):
    class Frob(object):
        def __enter__(self):
            print msg,
            return True
        def __exit__(self, type, value, traceback):
            if type is None:
                print "OK!"
            else:
                print "FAIL!"
            return False

    return Frob()

def get_mysql_root_connection():
    print "Enter MySQL credentials of a user who can create a database"
    
    root_login = raw_input("Login (default: root)> ")
    if root_login == '':
        root_login = 'root'
    root_passwd = getpass.getpass("Password> ")
    print ''
    return mysql.connector.connect(user=root_login,
                                   password=root_passwd,
                                   host='127.0.0.1')


if __name__ == '__main__':
    conn = get_mysql_root_connection()

    if zooey_db_exists_p(conn):
        if not get_y_or_n_answer("WARNING: zooey db already exists, do you want to proceed?",
                                 "Do you want to proceed?"):
            exit()
        print "Skipping creation of zooey db."
    else:
        with ok_or_fail_print("Creating zooey db ..."):
            create_zooey_db(conn)

    conn.close()

