from array import array
from contextlib import closing
import sys
import time

from javax.net.ssl import SSLContext, TrustManager, X509TrustManager
from java.net import URL

from org.apache.abdera import Abdera


# Modified from http://tech.pedersen-live.com/2010/10/trusting-all-certificates-in-jython/
# would be best to manage the trust store for something real

class TrustAllX509TrustManager(X509TrustManager):
    """Define a custom TrustManager which will blindly accept all certificates"""
    def checkClientTrusted(self, chain, auth):
        pass

    def checkServerTrusted(self, chain, auth):
        pass

    def getAcceptedIssuers(self):
        return None


def trust_all():
    trust_managers = array(TrustManager, [TrustAllX509TrustManager()])
    trust_all_context = SSLContext.getInstance("SSL")
    trust_all_context.init(None, trust_managers, None)
    SSLContext.setDefault(trust_all_context)


def read_events(feed_url, mark_id=None, read_back=200, poll_time=5.):
    # a given read of the feed is going to be reversed; use the urn as the mark
    count = 0
    abdera = Abdera()
    parser = abdera.getParser()

    def read_chunks(last_id):
        chunk_count = 0
        url = feed_url
        while chunk_count < read_back:
            with closing(URL(url).openStream()) as f:
                print >> sys.stderr, "Reading feed", url
                doc = parser.parse(f)
                feed = doc.getRoot()
                url = str(feed.getLinks("next")[0].href)
                for entry in feed.entries:
                    if last_id == entry.id:
                        return
                    yield entry
                    chunk_count += 1

    # combine loops together FIXME!
    last_id = None
    for entry in reversed(list(read_chunks(mark_id))):
        last_id = entry.id
        count += 1
        yield entry
    print >> sys.stderr, "Read", count, "events so far"
    while True:
        print >> sys.stderr, "Sleeping", poll_time, "then read to", last_id
        time.sleep(poll_time)
        for entry in reversed(list(read_chunks(last_id))):
            last_id = entry.id
            count += 1
            yield entry
        print >> sys.stderr, "Read", count, "events so far"


def main():
    trust_all()
    url = "https://atom.prod.dfw1.us.ci.rackspace.net/nova/events"
    last_updated = None
    seen = set()
    count = 0
    for event in read_events(url):
        if last_updated and event.updated < last_updated:
            print >> sys.stderr, "Out of order!!!!"
        if event.id in seen:
            print >> sys.stderr, "Duplicated", event.id
            continue
        print count, event.id, event.updated, [cat.term for cat in event.categories]

        last_updated = event.updated
        seen.add(event.id)
        
        if count >= 1000:
            break

        count += 1

main()
