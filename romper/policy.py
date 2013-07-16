from collections import defaultdict, namedtuple
import heapq
import logging


log = logging.getLogger("topology")


Observation = namedtuple("Observation", ["ts", "value"])


class Policy(object):

    # some bogus policy that might still show something interesting with storm

    def __init__(self, asg=None, age=300, low_watermark=0.2, high_watermark=0.9):
        self.asg = asg
        self.pool = defaultdict(list)
        self.age = age
        self.requested = 0
        self.low_watermark = low_watermark
        self.high_watermark = high_watermark

    def observe(self, key, ts, value):
        h = self.pool[key]
        heapq.heappush(h, Observation(ts, value))
        while h[0] < (ts - self.age, None):
            heapq.heappop(h)
        if not len(h):
            del self.pool[key]

        # FIXME because algebraic, could readily update values without rescan, so modify key_average accordingly

    def key_average(self, k):
        # 1, 0.8; 4, 0.5; 6, 0.9 - assume the value was 0.8 for [1, 2.5), 0.5 for [2.5, 5), 0.9. for [5, 6)
        items = sorted(self.pool[k]) # FIXME so very wrong! good for now
        if len(items) == 1:
            return items[0].value
        area = 0.
        for i in xrange(len(items)):
            if i > 0 and i < len(items) - 1:
                delta = (items[i+1].ts - items[i-1].ts)/2.
            elif i > 0:
                delta = (items[i].ts - items[i-1].ts)/2.
            else:
                delta = (items[i+1].ts - items[i].ts)/2.
            area += delta * items[i].value
            log.debug("i=%s, item=%s, delta=%s, area=%s", i, items[i], delta, area)
        return area / (items[-1].ts - items[0].ts)

    def average(self):
        if not self.pool:
            return None
        return sum(self.key_average(k) for k in self.pool.iterkeys())/len(self.pool)
        
    def request(self, amount):
        self.requested += amount

    def decide(self, asg):
        if self.asg is None:
            self.asg = asg  # ummm, hack! FIXME
        else:
            assert self.asg == asg
        pool_util = self.average()
        if pool_util < self.low_watermark:
            util_decision = -1
        elif pool_util > self.high_watermark:
            util_decision = 1
        else:
            util_decision = 0
        total_decision = util_decision + self.requested
        log.info("%s: schedule requested=%s, util=%s => util decision=%s, total decision=%s",
                 self.asg, self.requested, pool_util, util_decision, total_decision)
        return total_decision

    def ack_decision(self):
        self.requested = 0
