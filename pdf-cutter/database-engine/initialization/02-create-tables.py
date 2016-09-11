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

def get_mysql_zooey_connection():
    print "Enter MySQL credentials of zooey user"
    
    zooey_login = raw_input("Login (default: zooey)> ")
    if zooey_login == '':
        zooey_login = 'zooey'
    zooey_passwd = getpass.getpass("Password> ")
    print ''
    return mysql.connector.connect(user=zooey_login,
                                   password=zooey_passwd,
                                   host='127.0.0.1',
                                   database='zooey')

def create_cameras_table(conn):
    conn.cursor().execute('''
create table if not exists cameras (
    `camera_id` bigint(20) unsigned not null,
    `world_id` bigint(20) unsigned not null,
    `x` double not null,
    `y` double not null,
    `d` double not null,
    primary key(`camera_id`),
    key `world` (`world_id`))
''')
    print "Cameras table created"

def create_worlds_table(conn):
    conn.cursor().execute('''
create table if not exists worlds (
    `world_id` bigint(20) unsigned not null,
    `name` varchar(1000) character set utf8 not null default '',
    primary key(`world_id`))
''')
    print "Worlds table created"

def create_boxes_table(conn):
    conn.cursor().execute('''
create table if not exists boxes (
    `box_id` bigint(20) unsigned not null,
    `world_id` bigint(20) unsigned not null,
    `under_object_id` bigint(20) unsigned not null,
    `x` double not null,
    `y` double not null,
    `w` double not null,
    `h` double not null,
    `cut_line` double not null,
    primary key(`box_id`),
    key `world` (`world_id`),
    key `under_object` (`under_object_id`))
''')
    print "Boxes table created"

def create_under_objects_table(conn):
    conn.cursor().execute('''
create table if not exists under_objects (
    `under_object_id` bigint(20) unsigned not null,
    `a` int unsigned not null,
    `r` int unsigned not null,
    `g` int unsigned not null,
    `b` int unsigned not null,
    primary key(`under_object_id`))
''')
    print "Under objects table created"

def create_lock_table(conn):
    conn.cursor().execute('''
create table if not exists lock (
    `id` int unsigned not null,
    `pid` int(20) unsigned,
    primary key(`id`))
''')
    print "Lock table created"
    
    
if __name__ == '__main__':
    with zooey_lock():
        conn = get_mysql_zooey_connection()

        print "Successfully got a connection!"

        create_cameras_table(conn)
        create_worlds_table(conn)
        create_boxes_table(conn)
        create_under_objects_table(conn)
    
        conn.close()
    
