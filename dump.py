#!/usr/bin/python

import os
import re
import sys
import sqlite3
import HTMLParser

class Match():
    thread = None
    comment = None
    datetime = None

    def __init__(self, d, t, c):
        self.thread = t
        self.comment = c
        self.datetime = d

class MLStripper(HTMLParser.HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

columns = int(os.popen('stty size', 'r').read().split()[1])

dbName = "matches.db"
if not os.path.isfile(dbName):
    sys.stderr.write("Database does not exist. Exiting.\n")
    sys.exit(1)

con = sqlite3.connect(dbName)
dbc = con.cursor()

dbc.execute("SELECT datetime, thread, comment FROM matches")

matches = [ ]
for entry in dbc.fetchall():
    matches.append(Match(entry[0], entry[1], re.sub(r"(<br>)+", " ", HTMLParser.HTMLParser().unescape(entry[2]))))
for match in matches:
    string = strip_tags("%s - https://boards.4chan.org/x/thread/%s - %s" % (match.datetime, match.thread, match.comment))
    if not (len(sys.argv) > 1 and sys.argv[1] == "full") and len(string) > columns: string = string[:columns - 5] + "[...]"
    print(string)

con.close()
