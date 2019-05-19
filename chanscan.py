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

#==============================================================================#
# -- Uhhhhhh ----------------------------------------------------------------- #
#==============================================================================#

reload(sys) # tf this do
sys.setdefaultencoding('utf8')

#==============================================================================#
# -- Globals ----------------------------------------------------------------- #
#==============================================================================#

version           = "1.0"
debug             = False

opOnly            = True

honorHiro         = True
sleepTime         = 1
scanEvery         = 15

maxRetries        = 3

regex_terms       = [ "Hunger Games", "HG" ]
#regex_terms       = [ "Vox", "Beau" ]
#regex_terms       = [ "shit", "shitty" ]
match_regex       = '|'.join([ r"(\b%s\b)" % term for term in regex_terms ])

boardName         = "b"
apiroot_url       = "https://a.4cdn.org/%s/" % boardName
catalog_url       = apiroot_url + "catalog.json"
threads_url       = apiroot_url + "threads.json"
archive_url       = apiroot_url + "archive.json"
content_url       = lambda threadno : apiroot_url + "thread/" + threadno + ".json"

smtp_url          = "smtp.gmail.com"
smtp_port         = 587
email_address     = "chanscannotify@gmail.com"
email_password    = "6_2J@#hi~#soW2WT"

databaseName      = "matches.db"
create_statement  = "CREATE TABLE IF NOT EXISTS matches (thread TEXT PRIMARY KEY, datetime TEXT NOT NULL, comment TEXT)"
insert_statement  = lambda threadno, now, comment : "INSERT OR REPLACE INTO matches ('thread', 'datetime', 'comment') VALUES ('%s', '%s', '%s')" % (threadno, now, comment)
select_statement  = lambda entry : "SELECT thread FROM matches WHERE thread = '%s'" % entry

get_now           = lambda : datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")

#==============================================================================#
# -- Classes ----------------------------------------------------------------- #
#==============================================================================#

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

#==============================================================================#
# -- Functions --------------------------------------------------------------- #
#==============================================================================#

def sigint(signal, frame):
    sys.stdout.write("\nCaught SIGINT. Exiting.\n")
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
            return json.loads(urllib2.urlopen(urllib2.Request(url, headers={'User-Agent':'linux:chanscan:v0.1'}), timeout=30).read())
        except urllib2.HTTPError as e:
            if e.code == 404:
                return
            writeToStderr("(Attempt %d) HTTPError in '%s': %s" % (attempt, url, str(e)))
            time.sleep(sleepTime)

    writeToStderr("Couldn't retrieve JSON from API call '%s'" % threads_url)

    return None

def writeToStdout(string):
    columns = int(os.popen('stty size', 'r').read().split()[1])
    if len(line.strip()) > columns - 22: line = line[:columns - 28] + " [...]"
    sys.stdout.write("\r[%s] %s" % (get_now(), line.ljust(columns).strip()))
    sys.stdout.flush()

def writeToStderr(error):
    now = get_now()
    if debug == True: sys.stderr.write("\r[%s] %s\n" % (now, error))
    open("stderr.out", "a").write("[%s] %s\n" % (now, error))

def matchFound(threadno, comment):
    writeToStdout("boards.4chan.org/%s/thread/%s - %s\n" % (boardName, threadno, comment))
    #open("matches.txt", "a").write("%s - %s: %s\n" % (get_now(), threadno, comment))

    sendMail(threadno)
    dbAddEntry(threadno, get_now(), comment)

def sendMail(threadno):
    server = smtplib.SMTP(smtp_url, smtp_port)
    body   = "Dear Google, this isn't a spam bot, it's just an account I made for sending myself notifications from a pet project, which I threw together while drunk so it's kinda shitty."

    server.starttls()
    server.login(email_address, email_password)
    server.sendmail(email_address, email_address, "%s\n\n\n%s" % (threadno, body))
    server.quit()

def dbAddEntry(threadno, now, comment):
    con = sqlite3.connect(databaseName)
    dbc = con.cursor()

    dbc.execute(create_statement)
    dbc.execute(insert_statement(threadno, now, comment))

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

    msgBody = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (email_address, number1, subject, message)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(email_address, email_password)
    server.sendmail(email_address, number1, msgBody)
    server.sendmail(email_address, number3, msgBody)
    server.quit()

#==============================================================================#
# -- Main -------------------------------------------------------------------- #
#==============================================================================#

signal.signal(signal.SIGINT, sigint)

while True:
    pages = None
    last  = None

    #if debug: print("\nGetting list of threads...")
    writeToStdout("Getting threads...")
    for x in xrange(0, 3):
        try:
            pages = getData(threads_url) # Get all pages of a board
            break
        except Exception as e:
            writeToStderr("Exception encountered in getData('%s'): %s" % (threads_url, str(e)))
    if pages == None:
        writeToStderr("Unable to retrieve threads.")
        time.sleep(60)
        continue

    contents = None
    threads = [ Thread(page["page"], thread["no"], thread["last_modified"]) for page in pages for thread in page["threads"] ]
    counter = 0
    for thread in threads: # Traverse each thread.
        last = False
        counter += 1
        writeToStdout("Checking thread %s [page %s] (%d/%d)" % (thread.number, thread.page, counter, len(threads)))
        if debug: print("\nGetting thread...")
        for x in xrange(0, 3):
            try:
                contents = getData(content_url(thread.number)) # Get all posts in a thread.
                break
            except Exception as e:
                writeToStderr("Exception encountered in getData('%s'): %s" % (content_url(thread.number), str(e)))
        if contents:
            # ToDO: Also search subject, images, names, etc.
            for post in contents["posts"]: # Search each post in a thread for a regex match.
                if "com" in post: # Not all posts have a comment.
                    #if re.search(match_regex, str(post["com"]), flags=re.IGNORECASE) and not dbEntryExists(str(thread.number)) and not "voices of x" in str(post["com"]).lower(): # If a match was found, store it so we're not notified of the same match repeatedly.
                    if re.search(match_regex, str(post["com"]), flags=re.IGNORECASE) and not dbEntryExists(str(thread.number)) and not re.search("voices of /?x", str(post["com"]), flags=re.IGNORECASE): # If a match was found, store it so we're not notified of the same match repeatedly.
                        matchFound(thread.number, str(post["com"]))
                        last = True
                        break
                if opOnly == True:
                    continue
        else:
            if debug: print(" No contents!")

    if last == True:
        sys.stdout.write("\n")
    for x in xrange(0, scanEvery):
        writeToStdout("Thread scanning completed. Scanning again in %d minutes..." % (scanEvery - x))
        time.sleep(60)
