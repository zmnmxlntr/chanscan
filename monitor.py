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

def getData(url):
    if honorHiro == True:
        time.sleep(sleepTime)
    for attempt in xrange(0, maxRetries):
        try:
            return json.loads(urllib2.urlopen(urllib2.Request(url, headers={'User-Agent':'linux:chanscan:v0.1'}), timeout=30).read())
        except urllib2.HTTPError as e:
            if e.code == 404:
                return
            writeToStderr("(Attempt %d) HTTPError in '%s': %s" % (attempt, url, str(e)))
            time.sleep(sleepTime)
    writeToStderr("Couldn't retrieve JSON")
    return None

def matchFound(threadno, comment):
    writeToStdout("boards.4chan.org/%s/thread/%s - %s\n" % (boardName, threadno, comment))
    sendMail(threadno)

def sendMail(threadno):
    server = smtplib.SMTP(smtp_url, smtp_port)
    server.starttls()
    server.login(email_address, email_password)
    server.sendmail(email_address, email_address, "%s\n\n\nKeyword detected in HG thread" % (threadno))
    server.quit()

def dbAddEntry(threadno, now, comment):
    con = sqlite3.connect(databaseName)
    dbc = con.cursor()
    dbc.execute(create_statement)
    dbc.execute(insert_statement(threadno, now, comment))
    con.commit()
    con.close()

def writeToStderr(error):
    now = get_now()
    open("stderr.out", "a").write("[%s] %s\n" % (now, error))

def writeToStdout(string):
    sys.stdout.write("\r%s\r%s" % (''.ljust(int(os.popen('stty size', 'r').read().split()[1])), string))
    sys.stdout.flush()

def sigint(signal, frame):
    sys.stdout.write("\nCaught SIGINT. Exiting.\n")
    sys.exit(0)

#==============================================================================#
# -- Stuff ------------------------------------------------------------------- #
#==============================================================================#

reload(sys)
sys.setdefaultencoding('utf8')

signal.signal(signal.SIGINT, sigint)

#==============================================================================#
# -- Globals ----------------------------------------------------------------- #
#==============================================================================#

honorHiro       = False
sleepTime       = 1
scanEvery       = 5

maxRetries      = 3

regex_terms     = [ "Virginia", "zmnmxlntr", "tool", "script" ]
match_regex     = '|'.join([ r"(%s)" % term for term in regex_terms ])

boardName         = "b"
apiroot_url       = "https://a.4cdn.org/%s/" % boardName
content_url       = lambda threadno : apiroot_url + "thread/" + threadno + ".json"

smtp_url        = "smtp.gmail.com"
smtp_port       = 587
email_address   = "chanscannotify@gmail.com"
email_password  = "6_2J@#hi~#soW2WT"

databaseName    = "matches.db"

get_now         = lambda : datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")

#==============================================================================#
# -- Main -------------------------------------------------------------------- #
#==============================================================================#

while True:
    matches = [ ]

    if not os.path.isfile(databaseName):
        sys.stderr.write("Database does not exist. Exiting.\n")
        sys.exit(1)
    con = sqlite3.connect(databaseName)
    dbc = con.cursor()
    dbc.execute("SELECT thread FROM matches")
    for entry in dbc.fetchall():
        matches.append(entry[0])
    con.close()

    for match in matches:
        content = None
        for x in xrange(0, 3):
            try:
                contents = getData(content_url(match)) # Get all posts in a thread.
                break
            except Exception as e:
                writeToStderr("Exception encountered: %s" % str(e))
        if contents:
            for post in contents["posts"]: # Search each post in a thread for a regex match.
                if "com" in post: # Not all posts have a comment.
                    if re.search(match_regex, str(post["com"]), flags=re.IGNORECASE): # If a match was found, store it so we're not notified of the same match repeatedly.
                        matchFound(match, str(post["com"]))
                        break

    for x in xrange(0, scanEvery):
        writeToStdout("Thread scanning completed. Scanning again in %d minutes..." % (scanEvery - x))
        time.sleep(60)
