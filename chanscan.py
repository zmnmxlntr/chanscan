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

debug             = False

honorHiro         = True
sleepTime         = 1

maxRetries        = 3

match_regex       = r"(\bVox\b)|(\bBeau\b)"

apiroot_url       = "https://a.4cdn.org/x/"
catalog_url       = apiroot_url + "catalog.json"
threads_url       = apiroot_url + "threads.json"
archive_url       = apiroot_url + "archive.json"
content_url       = lambda threadno : apiroot_url + "thread/" + threadno + ".json"

smtp_url          = "smtp.gmail.com"
smtp_port         = 587
sender_address    = "chanscannotify@gmail.com"
sender_password   = "6_2J@#hi~#soW2WT"
recipient_address = "jaredjpruett@gmail.com"

databaseName      = "matches.db"
create_statement  = "CREATE TABLE IF NOT EXISTS matches (thread TEXT PRIMARY KEY, datetime TEXT NOT NULL, comment TEXT)"
insert_statement  = lambda threadno, now, comment : "INSERT OR REPLACE INTO matches ('thread', 'datetime', 'comment') VALUES ('%s', '%s', '%s')" % (threadno, now, comment)
select_statement  = lambda entry : "SELECT thread FROM matches WHERE thread = '%s'" % entry

get_now           = lambda : datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")

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

    for attempt in xrange(0, maxRetries):
        try:
            return json.loads(urllib2.urlopen(url).read())
        except Exception as e:
            writeToStderr("(Attempt %d) HTTPError in '%s': %s" % (attempt, url, str(e)))

    writeToStderr("Couldn't retrieve JSON from API call '%s'" % threads_url)

    return None

def writeToStdout(string):
    sys.stdout.write("\r%s\r%s" % (''.ljust(int(os.popen('stty size', 'r').read().split()[1])), string))
    sys.stdout.flush()

def writeToStderr(error):
    now = get_now()
    if debug == True: sys.stderr.write("\r[%s] %s\n" % (now, error))
    open("stderr.txt", "a").write("%[%s] %s\n" % (now, error))

def matchFound(threadno, comment):
    now = get_now()

    writeToStdout("Found a match in thread %s\n" % threadno)
    open("matches.txt", "a").write("%s - %s: %s\n" % (now, threadno, comment))

    body = "Dear Google, this isn't a spam bot, it's just an account I made for sending myself notifications from a pet project, which I threw together while drunk so it's kinda shitty."
    server = smtplib.SMTP(smtp_url, smtp_port)
    server.starttls()
    server.login(sender_address, sender_password)
    server.sendmail(sender_address, recipient_address, "%s\n\n\n%s" % (threadno, body))
    server.quit()

    con = sqlite3.connect(databaseName)
    dbc = con.cursor()

    dbc.execute(create_statement)
    dbc.execute(insert_st(threadno, now, comment))

    con.commit()
    con.close()

def dbEntryExists(entry):
    con = sqlite3.connect(databaseName)
    dbc = con.cursor()

    dbc.execute(create_statement)
    dbc.execute(select_statement(entry))

    found = len(dbc.fetchall())

    con.close()

    return found

def sendSMS():
    number1 = "2543008192@msg.fi.google.com"
    number2 = "2547215847@tmomail.net"
    number3 = "2547215847@msg.fi.google.com"
    subject = "This here is a test notification"
    message = "This is a test message for the shitty notification daemon I'm writing. Kindly allow it to pass through, and such."

    msgbody = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (sender_address, number1, subject, message)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_address, sender_password)
    server.sendmail(sender_address, number1, msgbody)
    server.sendmail(sender_address, number3, msgbody)
    server.quit()

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#

signal.signal(signal.SIGINT, sigint)

while True:
    pages = getData(threads_url) # Get all pages of a board
    if pages == None:
        sys.exit(1)
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
                    if re.search(match_regex, str(post["com"]), flags=re.IGNORECASE) and not dbEntryExists(str(thread.number)): # If a match was found, store it so we're not notified of the same match repeatedly.
                        matchFound(thread.number, str(post["com"]))
                        last = True
                        break

    if last == True: sys.stdout.write("\n")
    writeToStdout("Thread scanning completed. Sleeping for ten minutes.")
    time.sleep(3600)

