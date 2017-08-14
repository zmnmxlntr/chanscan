import urllib2
import json
import time
import re

board       = "/x/"
regex       = r"(\b[^/]Vox[^/]\b)|(\bBeau\b)"

root_url    = "https://a.4cdn.org" + board
catalog_url = root_url + "catalog.json"
threads_url = root_url + "threads.json"
archive_url = root_url + "archive.json"

class Thread():
    page = None
    number = None
    modified = None
    contents = None

    def __init__(self, page, number, modified):
        self.page = str(page)
        self.number = str(number)
        self.modified = str(modified)

    def __str__(self):
        return "[%s]: %s" % (self.page, self.number)

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
    except: # URL not found
        data = None

    time.sleep(1) # One request per second

    return data

def main():
    data = getData(threads_url)
    threads = [ ]

    for page in data:
        for thread in page["threads"]:
            threads.append(Thread(page["page"], thread["no"], thread["last_modified"]))

    for thread in threads:
        print "Parsing thread %s [page %s]" % (thread.number, thread.page)

        contents = getData(root_url + "thread/" + thread.number + ".json")
        if contents:
            for post in contents["posts"]: # TODO: Also search subject, images, names, etc.
                try: # Wrap in try because not all posts have a comment
                    search = re.search(regex, str(post["com"]), flags=re.IGNORECASE)
                    if search:
                        print "%s: %s" % (thread.number, str(post["com"]))
                except:
                    pass

main()
