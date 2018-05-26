#!/usr/bin/python

import datetime
import smtplib
import sqlite3
import urllib2
import signal
import json
import time
import sys
import os
import re

#------------------------------------------------------------------------------#
# Uhhhhhh                                                                      #
#------------------------------------------------------------------------------#

reload(sys) # tf this do
sys.setdefaultencoding('utf8')

#------------------------------------------------------------------------------#
# Globals                                                                      #
#------------------------------------------------------------------------------#

debug       = False

retries     = 3

honorHiro   = True
sleepTime   = 1

regex       = r"(\bVox\b)|(\bBeau\b)"

apiroot_url = "https://a.4cdn.org/x/"
catalog_url = apiroot_url + "catalog.json"
threads_url = apiroot_url + "threads.json"
archive_url = apiroot_url + "archive.json"
content_url = lambda threadno : apiroot_url + "thread/" + threadno + ".json"

get_now     = lambda : datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")

dbName      = "matches.db"

#------------------------------------------------------------------------------#
# Classes                                                                      #
#------------------------------------------------------------------------------#

class Thread():
    page = None
    number = None
    modified = None

    def __init__(self, page, number, modified):
        self.page = str(page)
        self.number = str(number)
        self.modified = str(modified)

    def __str__(self):
        return "[%s]: %s" % (self.page, self.number)

#------------------------------------------------------------------------------#
# Functions                                                                    #
#------------------------------------------------------------------------------#

def sigint(signal, frame):
    sys.stderr.write("\nCaught SIGINT. Exiting.\n")
    sys.exit(0)

def getPretty(data):
    return json.dumps(data, indent=4)

def dumpToFile(contents):
    fout = open("dump", "w")
    for content in contents:
        fout.write(str(content) + "\n")
    fout.close()

def getData(url):
    if honorHiro == True:
        time.sleep(sleepTime)

    for attempt in xrange(0, retries):
        try:
            return json.loads(urllib2.urlopen(url).read())
        except Exception as e:
            writeToStderr("[%s] [Attempt %d] HTTPError in '%s': %s" % (get_now(), attempt, url, str(e)))

    sys.stderr.write("\nCouldn't retrieve JSON from API call '%s'\n" % threads_url)
    sys.exit(1)

def writeToStdout(string):
    sys.stdout.write("\r%s\r%s" % (''.ljust(int(os.popen('stty size', 'r').read().split()[1])), string))
    sys.stdout.flush()

def writeToStderr(error):
    sys.stderr.write("\n" % error)
    open("stderr.txt", "a").write("\n%s\n" % error)

def matchFound(threadno, comment):
    now = get_now()

    writeToStdout("Found a match in thread %s\n" % threadno)
    open("matches.txt", "a").write("%s - %s: %s\n" % (now, threadno, comment))

    body = "Dear Google, this isn't a spam bot, it's just an account I made for sending myself notifications from a pet project, which I threw together while drunk so it's kinda shitty."
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login("chanscannotify@gmail.com", "6_2J@#hi~#soW2WT")
    server.sendmail("chanscannotify@gmail.com", "jaredjpruett@gmail.com", "%s\n\n\n%s" % (threadno, body))
    server.quit()

    con = sqlite3.connect(dbName)
    db = con.cursor()
    db.execute("CREATE TABLE IF NOT EXISTS matches (thread TEXT PRIMARY KEY, datetime TEXT NOT NULL)")
    db.execute("INSERT OR REPLACE INTO matches ('thread', 'datetime') VALUES ('%s', '%s')" % (threadno, now))
    con.commit()
    con.close()

def dbEntryExists(entry):
    con = sqlite3.connect(dbName)
    db = con.cursor()
    db.execute("CREATE TABLE IF NOT EXISTS matches (thread TEXT PRIMARY KEY, datetime TEXT NOT NULL)")
    db.execute("SELECT thread FROM matches WHERE thread = '%s'" % entry)
    found = len(db.fetchall())
    con.close()
    return found

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#

signal.signal(signal.SIGINT, sigint)

while True:
    pages = getData(threads_url) # Get all pages of a board
    threads = [ ]
    for page in pages:
        for thread in page["threads"]: # Get all of a board's active threads.
            threads.append(Thread(page["page"], thread["no"], thread["last_modified"]))
    for thread in threads: # Traverse each thread.
        last = False
        writeToStdout("Parsing threads: %s [page %s]..." % (thread.number, thread.page))
        contents = getData(content_url(thread.number)) # Get all posts in a thread.
        if contents:
            # ToDO: Also search subject, images, names, etc.
            for post in contents["posts"]: # Search each post in a thread for a regex match.
                if "com" in post: # Not all posts have a comment.
                    if re.search(regex, str(post["com"]), flags=re.IGNORECASE) and not dbEntryExists(str(post["com"])): # If a match was found, store it so we're not notified of the same match repeatedly.
                        matchFound(thread.number, str(post["com"]))
                        last = True
                        break

    if last == True: sys.stdout.write("\n")
    writeToStdout("Thread scanning completed. Sleeping for ten minutes.")
    time.sleep(3600)
