#!/usr/bin/python

import os
import sys
import sqlite3

dbName = "matches.db"

if not os.path.isfile(dbName):
    sys.stderr.write("Database does not exist. Exiting.\n")
    sys.exit(1)

con = sqlite3.connect(dbName)
dbc = con.cursor()

dbc.execute("SELECT datetime, thread FROM matches")
for entry in dbc.fetchall():
    print("[%s] %s" % (entry[0], entry[1]))

con.close()
