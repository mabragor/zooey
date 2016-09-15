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

PATCHES_LOADED_JUST_NOW = {}

class DoublePut(Exception):
    def __init__(self, macro_id):
        super(DoublePut, self).__init__()
        self.macro_id = macro_id
    # TODO : how to actually write nice error messages here?
    def __str__(self):
        return "Trying to double-put a commit with same macro id " + self.macro_id

def put_commit_in_hash(commit):
    global LOADED_PATCHES
    global PATCHES_LOADED_JUST_NOW
    if commit is not None:
        if commit['macro_id'] in LOADED_PATCHES:
            raise DoublePut(commit['macro_id'])
        LOADED_PATCHES[commit['macro_id']] = commit
        PATCHES_LOADED_JUST_NOW[commit['macro_id']] = True
        link_commit(commit)

def link_commit(commit):
    parent_id = commit['parent_macro_id']
    other_commit = LOADED_PATCHES.get(parent_id, None)
    if other_commit is not None:
        commit.prev = other_commit
        other_commit.next[commit['macro_id']] = commit
        
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
            'micro_ids' : [ {'id' : first[0], 'id' : first[5]} ],
            'next' : {},
            'prev' : None }
    # I wonder, if this doesn't re-yield the first item
    for (id, _, _, _, msg) in cursor:
        res['micro_ids'].append({'id' : id, 'msg' : msg})
    cursor.close()

    put_commit_in_hash(res)
        
    return res

def put_commits_to_hash_from_cursor(cursor):
    # closest to the root commit will be first one returned, thanks to the order-by clause
    new_commit = None
    first_time = True
    first_commit = None
    count = 0
    for (id, macro_id, parent_macro_id, msg) in cursor:
        count += 1
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

    return (first_commit, count)

def load_backward_branch(conn, macro_id, size=None):
    '''Load a number of commits in the same branch, which are closer to the root,
       return commit closest to the root and number of commits actually loaded.'''
    commit = ensure_loaded(conn, macro_id)
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

    (first_commit, count) = put_commits_to_hash_from_cursor(cursor)
        
    # we need to link the commit we started from to this newly ordered chain
    link_commit(LOADED_PATCHES[macro_id])

    return (first_commit, count)

def ensure_loaded(conn, macro_id):
    '''Ensures, commit with specified macro_id is loaded from the DB.'''
    if macro_id not in LOADED_PATCHES:
        load_commit(conn, macro_id)
    return LOADED_PATCHES[macro_id]

def load_backward_branch_iter(conn, macro_id, size):
    '''On each NEXT load new portion of commits that are closer to the root. Size varies highly.'''
    commit = ensure_loaded(conn, macro_id)

    while True:
        if commit['parent_macro_id'] == 0:
            break
        (new_commit, count) = load_backward_branch(conn, commit['macro_id'], size)
        if count != 0:
            commit = new_commit
            yield count
        else:
            new_commit = ensure_loaded(conn, commit['parent_macro_id'])
            link_commit(commit)
            commit = new_commit
            yield 1

def bunch_balancer(optimal_size, iter1):
    while True:
        cur_size = 0
        try:
            while cur_size >= optimal_size:
                cur_size += iter1.next()
        except StopIteration:
            yield cur_size
            break
        else:
            yield cur_size
            
        
            
BUNCH_SIZE = 50

def try_load_next_bunch(conn, iter1):
    while True:
        try:
            star_iter.next()
        except DoublePut as e:
            if PATCHES_LOADED_JUST_NOW.get(e.macro_id, False):
                # we've found our common point
                return (None, e.macro_id)
            else:
                star_iter = bunch_balancer(BUNCH_SIZE,
                                           load_backward_branch_iter(conn,
                                                                     find_branch_beginning(e.macro_id),
                                                                     BUNCH_SIZE))
        else:
            return (star_iter, None)
    

def find_branch_beginning(macro_id):
    global LOADED_PATCHES
    global PATCHES_LOADED_JUST_NOW

    commit = LOADED_PATCHES[macro_id]
    while True:
        PATCHES_LOADED_JUST_NOW[commit['macro_id']] = True
        parent_id = commit['parent_macro_id']
        if parent_id is None:
            return commit['macro_id']
        commit = LOADED_PATCHES[parent_id]

        
def load_until_common_commit(conn, db_snapshot_id, work_stop_id):
    star_iter = bunch_balancer(BUNCH_SIZE, load_backward_branch_iter(conn, db_snapshot_id, BUNCH_SIZE))
    box_iter = bunch_balancer(BUNCH_SIZE, load_backward_branch_iter(conn, work_stop_id, BUNCH_SIZE))

    star_iter_depleted = False
    box_iter_depleted = False
    
    while (not star_iter_depleted) or (not box_iter_depleted):
        try:
            (star_iter, macro_id) = try_load_next_bunch(conn, star_iter)
            if macro_id is not None:
                return macro_id
        except StopIteration:
            star_iter_depleted = True

        try:
            (box_iter, macro_id) = try_load_next_bunch(conn, box_iter)
            if macro_id is not None:
                return macro_id
        except StopIteration:
            box_iter_depleted = True
            
    raise Exception("Common ancestor of star and box was not found!")

def mysql_macro_ids_iter(patches, size):
    count = 0
    lst = []
    for macro_id in patches.iterkeys():
        lst.append(macro_id)
        count += 1
        if count == size:
            yield '(' + ', '.join(lst) + ')'
            count = 0
            lst = []
    if count != 0:
        yield '(' + ', '.join(lst) + ')'
                
        

def load_all_branchlings(conn):
    # we need a copy, because as we start to execute the queries loading new patches,
    # PATCHES_LOADED_JUST_NOW will be changing
    patches = PATCHES_LOADED_JUST_NOW.copy()

    query_template_before = ('select id, macro_id, parent_macro_id, branch_id, msg from history'
                             + ' where parent_macro_id in ')
    query_template_after = ' order by id'
    for macro_ids in mysql_macro_ids_iter(patches, BUNCH_SIZE):
        cur = conn.cursor()
        cur.execute(query_template + macro_ids + query_template_after)
        put_commits_to_hash_from_cursor(cur)

    
def load_latest_history(conn, db_snapshot_id, work_stop_id):
    global PATCHES_LOADED_JUST_NOW
    PATCHES_LOADED_JUST_NOW = {}
    load_until_common_commit(conn, db_snapshot_id, work_stop_id)
    load_all_branchlings(conn)



