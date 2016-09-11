#!/usr/bin/python2

from __future__ import with_statement

import readline
import getpass

import mysql.connector
import sys

from utils import zooey_lock

READLINE_CONFIG = '''
set bell-style none
set disable-completion on
'''

ZOOEY_DB_NAME = 'zooey'

for line in READLINE_CONFIG.split("\n"):
    print line
    readline.parse_and_bind(line)

def db_exists_p(conn, db_name=ZOOEY_DB_NAME):
    cur = conn.cursor()
    cur.execute("show databases like %(db_name)s", { 'db_name' : db_name })
    res = list(cur)
    # print res
    return len(res) != 0

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

def user_exists_p(conn, username):
    cursor = conn.cursor()
    cursor.execute("select exists(select 1 from mysql.user where user = %(username)s)",
                   {'username' : username})
    (num,) = cursor.fetchone()
    if num == 0:
        return False
    elif num == 1:
        return True
    else:
        raise Exception("Unexpected result from SQL: %s" % num)

def create_localhost_user(conn, username, password):
    cursor = conn.cursor()
    cursor.execute("create user %(username)s@'localhost' identified by %(password)s;",
                   { 'username' : username, 'password' : password })

def drop_localhost_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("drop user %(username)s@'localhost';",
                   { 'username' : username })
    
def grant_all_priv_on_a_database(conn, username, db):
    cursor = conn.cursor()
    escaped_db = conn.converter.escape(db)
    # print escaped_db
    cursor.execute("grant all on " + escaped_db + ".* to %(username)s@'localhost';",
                   { 'username' : username })

def create_zooey_user_with_correct_priviliges():
    zooey_passwd = None
    while True:
        zooey_passwd1 = getpass.getpass("Please, enter password for new zooey user> ")
        zooey_passwd2 = getpass.getpass("Please, type this password one more time> ")
        if zooey_passwd1 != zooey_passwd2:
            print "Passwords you entered don't match, please, try again"
        else:
            zooey_passwd = zooey_passwd1
            break
    print ''
    with ok_or_fail_print("Creating new zooey user ..."):
        create_localhost_user(conn, 'zooey', zooey_passwd)
        grant_all_priv_on_a_database(conn, 'zooey', 'zooey')

if __name__ == '__main__':
    with zooey_lock():
        conn = get_mysql_root_connection()

        if db_exists_p(conn):
            if not get_y_or_n_answer("WARNING: zooey db already exists, do you want to proceed?",
                                     "Do you want to proceed?"):
                exit()
            print "Skipping creation of zooey db."
        else:
            with ok_or_fail_print("Creating zooey db ..."):
                create_zooey_db(conn)

        if user_exists_p(conn, 'zooey'):
            # TODO : check that permissions are right
            if get_y_or_n_answer("zooey user already exists : do you want to recreate it?",
                                 "Do you want to recreate a user?"):
                drop_localhost_user(conn, 'zooey')
                create_zooey_user_with_correct_priviliges()
            else:
                print "Skipping creation of zooey user."
        else:
            create_zooey_user_with_correct_priviliges()
            
        conn.close()

