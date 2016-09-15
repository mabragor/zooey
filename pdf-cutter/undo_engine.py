### undo_engine.py
### The thing that remembers everything the user does (in the form of the tree)
### and allows to conveniently view this history (and import some sequences of "patches" to other brances)

from __future__ import with_statement

import mysql.connector
import sys

from utils import (mysql_zooey_connection)

# OK, for now we assume we have just one global history
# We will correct for this later

def create_history_table(conn):
    conn.cursor().execute('''
create table if not exists history (
    `id` bigint(64) unsigned not null,
    `macro_id` bigint(64) unsigned not null,
    `parent_macro_id` bigint(64) unsigned not null,
    `branch_id` bigint(64) unsigned not null,
    `msg` varchar(1000) not null,
    primary key(`id`),
    key `macro_id` (`macro_id`),
    key `parent_macro_id` (`parent_macro_id`),
    key `branch_id` (`branch_id`),
    engine = InnoDB
''')
    print ("history table created")

LOADED_PATCHES={}

def put_commit_in_hash(commit):
    global LOADED_PATCHES
    if commit is not None:
        if commit['macro_id'] in LOADED_PATCHES:
            raise Exception("Trying to double-put a commit with same macro id " + commit['macro_id'])
        LOADED_PATCHES[commit['macro_id']] = commit

def load_commit(conn, macro_id):
    cur = conn.cursor()
    cur.execute('select id, macro_id, parent_macro_id, branch_id, msg from history'
                + ' where macro_id = %(macro_id)s order by id', { 'macro_id' : macro_id })

    first = cur.fetchone()
    if first is None:
        cur.close()
        raise Exception("Commit with macro_id %s wasn't found in history table" % (macro_id,))
    res = { 'macro_id' : first[1],
            'parent_macro_id' : first[2],
            'branch_id' : first[3],
            'micro_ids' : [ {'id' : first[0], 'id' : first[5]} ] }
    # I wonder, if this doesn't re-yield the first item
    for (id, _, _, _, msg) in cursor:
        res['micro_ids'].append({'id' : id, 'msg' : msg})
    cursor.close()

    put_commit_in_hash(res)
        
    return res

def load_backward_branch(conn, macro_id, size=None):
    '''Load a number of commits in the same branch, which are closer to the root,
       return commit closest to the root.'''
    if macro_id not in LOADED_PATCHES:
        load_commit(conn, macro_id)
    commit = LOADED_PATCHES[macro_id]
    cur = conn.cursor()

    if size is None:
        query = ('select id, macro_id, parent_macro_id, msg from history'
                 + ' where branch_id = %(branch_id)s and'
                 + ' macro_id < %(macro_id)s'
                 + ' order by id')
        cursor.execute(query, { 'branch_id' : commit['branch_id'], 'macro_id' : commit['macro_id'] })
    else:
        query = ('select id, macro_id, parent_macro_id, msg from history'
                 + ' where branch_id = %(branch_id)s and'
                 + ' (macro_id <= %(macro_id_min)s and macro_id < %(macro_id_max)s)'
                 + ' order by id')
        cursor.execute(query, { 'branch_id' : commit['branch_id'],
                                'macro_id_min' : commit['macro_id'] - size,
                                'macro_id_max' : commit['macro_id']})

    # closest to the root commit will be first one returned, thanks to the order-by clause
    new_commit = None
    first_time = True
    first_commit = None
    for (id, macro_id, parent_macro_id, msg) in cursor:
        if new_commit is None or macro_id != new_commit['macro_id']:
            put_commit_in_hash(new_commit)
            if first_time:
                first_time = False
                first_commit = new_commit
            new_commit = { 'macro_id' : macro_id,
                           'parent_macro_id' : parent_macro_id,
                           'branch_id' : commit['branch_id'],
                           'micro_ids' : [ {'id' : id, 'msg' : msg} ] }
        else:
            new_commit['micro_ids'].append({'id' : id, 'msg' : msg})
    put_commit_in_hash(new_commit)
    return first_commit

def load_until_common_commit(conn, db_snapshot_id, work_stop_id):
    pass

def load_latest_history(conn, db_snapshot_id, work_stop_id):
    load_until_common_commit(conn, db_snapshot_id, work_stop_id)
    load_all_branchlings(conn)



