from collections import deque
from contextlib import closing
import time

from backtype.storm.topology.base import BaseRichSpout
from backtype.storm.tuple import Fields, Values
from java.net import URL
from org.apache.abdera import Abdera
from org.slf4j import LoggerFactory

from clamp import PackageProxy
from romper.trust import trust_all_certificates


# still need to implement consistent hashing if this will be used at large scale
# on the other hand, currently we see 1 event/s/data center for status updates, which can be readily handled
# with just one instance of the spout

# Make transactional; see https://github.com/nathanmarz/storm/wiki/Trident-state
# and https://github.com/nathanmarz/storm/wiki/Trident-spouts
# specifically opaque transactional support, such as seen in 
# https://github.com/nathanmarz/storm-contrib/blob/master/storm-kafka/src/jvm/storm/kafka/trident/OpaqueTridentKafkaSpout.java


class AtomSpout(BaseRichSpout):
    # FIXME doc the conf requirements

    __proxymaker__ = PackageProxy("otter")

    def open(self, conf, context, collector):
        if conf.get("trust_all_certificates"):
            trust_all_certificates()
        self.collector = collector
        self.last_time = time.time()

        # FIXME get last_id from ZK; also consider how to partition
        # with consistent hashing
        self.readers = [AtomReader(feed_url) for feed_url in conf["atom_feeds"]]

    def nextTuple(self):
        for reader in self.readers:
            for event in reader.read_events():
                self.collector.emit(Values([event.updated, event]))
        # FIXME update last_id per feed in ZK

        # FIXME low pri, but should make configurable
        # Also, in the event of lengthy disconnect we may also see rate limiting
        time.sleep(1.)

    def declareOutputFields(self, declarer):
        declarer.declare(Fields(["ts", "event"]))


# NOTE keep this as a distinct, testable piece of code


class SeenWindow(object):
    """Keeps track of what has been seen for `window` number of items"""

    def __init__(self, window=500):
        self.seen = set()
        self.purgeq = deque()
        self.window = window

    def add(self, item):
        self.seen.add(item)
        self.purgeq.append(item)
        if len(self.purgeq) > self.window:
            old = self.purgeq.popLeft()
            self.seen.remove(old)

    def __contains__(self, item):
        return item in self.seen


class AtomReader(object):

    def __init__(self, feed_url, read_back_pages=200, last_id=None):
        self.feed_url = feed_url
        self.read_back_pages = read_back_pages
        self.last_id = last_id
        self.parser = Abdera().getParser()
        self.seen = SeenWindow()
        self.last_updated = None
        self.total_events = 0
        self.log = LoggerFactory.getLogger(AtomReader)

    def _read_pages(self):
        """Reads pages from the feed, from newest to oldest (reverse chronology)"""
        page_count = 0
        url = self.feed_url
        while page_count < self.read_back_pages:  # FIXME what if we exhaust our pages?
            with closing(URL(url).openStream()) as f:
                self.log.debug("Reading feed: {}", url)
                doc = self.parser.parse(f)
                feed = doc.getRoot()
                url = str(feed.getLinks("next")[0].href)
                for entry in feed.entries:
                    if self.last_id == entry.id:
                        return  # done given read back to last_id
                    yield entry
                    page_count += 1

    def read_events(self):
        """Deliver events from oldest to newest, with some minimal sanity checking"""
        count = 0
        for event in reversed(list(self._read_pages())):
            if self.last_updated and event.updated < self.last_updated:
                self.log.warn("Ignoring out of order event in feed {}: {} ({}) is older than previous event {}",
                         self.feed_url, event.id, event.updated, self.last_updated)
                continue
            if event.id in self.seen:
                self.log.warn("Ignoring duplicated event in feed {}: {}", self.feed_url, event.id)
                continue
            self.last_updated = event.updated
            self.seen.add(event.id)
            self.last_id = event.id
            count += 1
            yield event

        # FIXME storm supports metrics. use that functionality.
        self.total_events += count
        self.log.debug("Read {} of {} events from feed {}", count, self.total_events, self.feed_url)
