
import psycopg2

try:
    conn = psycopg2.connect("dbname='zooey' user='zooey'")
    print "Connected successfully"
except:
    print "Unable to connect"
    raise
