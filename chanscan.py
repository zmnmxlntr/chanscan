import datetime
import smtplib
import urllib2
import signal
import json
import time
import sys
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

honorHiro   = True
sleepTime   = 1

stringWidth = 80

board       = "/x/"
regex       = r"(\bVox\b)|(\bBeau\b)"

website_url = "https://a.4cdn.org/" + board
catalog_url = website_url + "catalog.json"
threads_url = website_url + "threads.json"
archive_url = website_url + "archive.json"
content_url = lambda threadno : website_url + "thread/" + threadno + ".json"

get_now     = lambda : datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")

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
    try:
        data = json.loads(urllib2.urlopen(url).read())
    except Exception as e:
        data = None
        sys.stderr.write("\nHTTPError in '%s': %s\n" % url, str(e))

    if honorHiro == True:
        time.sleep(sleepTime)

    return data

def writeToConsole(string):
    sys.stdout.write(("{0:%d}" % stringWidth).format("\r%s" % string))
    sys.stdout.write("\033[%dD" % (stringWidth - len(string) - 1))
    sys.stdout.flush()

def matchFound(threadno, comment):
    writeToConsole("Found a match in thread %s" % threadno)
    open("matches.txt", "a").write("%s - %s: %s\n" % (get_now(), threadno, comment))

    body = "Dear Google, this isn't a spam bot, it's just an account I made for sending myself notifications from a pet project, which I threw together while drunk so it's kinda shitty."
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login("chanscannotify@gmail.com", "6_2J@#hi~#soW2WT")
    server.sendmail("chanscannotify@gmail.com", "jaredjpruett@gmail.com", "%s\n\n\n%s" % (threadno, body))
    server.quit()
 
#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#

signal.signal(signal.SIGINT, sigint)

reported = [ ]
while True:
    pages = getData(threads_url) # Get all pages of a board
    if not pages:
        sys.stderr.write("\nCouldn't retrieve JSON from API call '%s'\n" % threads_url)
        sys.exit(1)

    threads = [ ]
    for page in pages:
        for thread in page["threads"]: # Get all of a board's active threads.
            threads.append(Thread(page["page"], thread["no"], thread["last_modified"]))
    for thread in threads: # Traverse each thread.
        last = False
        writeToConsole("Parsing threads: %s [page %s]..." % (thread.number, thread.page))
        contents = getData(content_url(thread.number)) # Get all posts in a thread.
        if contents:
            for post in contents["posts"]: # Search each post in a thread for a regex match. ToDO: Also search subject, images, names, etc.
                if "com" in post: # Not all posts have a comment.
                    if re.search(regex, str(post["com"]), flags=re.IGNORECASE) and str(thread.number) not in reported: # If a match was found, report it and store it so it's not reported repeatedly.
                        matchFound(thread.number, str(post["com"]))
                        reported.append(thread.number)
                        last = True
                        break

    if last == True: sys.stdout.write("\n")
    writeToConsole("Thread scanning completed. Sleeping for ten minutes.")
