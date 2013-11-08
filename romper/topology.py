import logging  # FIXME replace with log4j (or twiggy if that makes sense)
import random
import time
from collections import defaultdict
from functools import partial

from backtype.storm import Config, Constants
from backtype.storm.topology import TopologyBuilder
from backtype.storm.topology.base import BaseRichBolt, BaseRichSpout
from backtype.storm.tuple import Fields, Values

from clamp import ClampProxyMaker
from romper.policy import Policy


logging.basicConfig(
    filename="demo-topology.log", level=logging.INFO,
    format="%(process)d %(threadName)s %(asctime)s %(funcName)s %(message)s"
)
log = logging.getLogger("topology")


server_cpu = {
    "foo": [0.88, 0.99],
    "bar": [0.1, 0.3],
    "foobar": [0.2, 0.4],
    "fum": [0.85, 0.95],
    "web": [0.5, 1.],
    "db": [0.9, 1.],
}

server2asg = {}

for asg in server_cpu.iterkeys():
    for i in xrange(5):
        server = "%s-%s" % (asg, i)
        server2asg[server] = asg


def lookup_asg(server):
    # what if server is not known? throw away? what happens when a bolt has an exception?
    # does it get re-executed if transactional? probably
    return server2asg[server]


# FIXME at some point promote into a stormlib package; but figure out storm more

def is_tick_tuple(t):
    return t.getSourceComponent() == Constants.SYSTEM_COMPONENT_ID and \
        t.getSourceStreamId() == Constants.SYSTEM_TICK_STREAM_ID


class MonitoringSpout(BaseRichSpout):

    __proxymaker__ = ClampProxyMaker("otter")

    def open(self, conf, context, collector):
        self._collector = collector
        self.last_time = time.time()

    def nextTuple(self):
        time.sleep(random.uniform(0.95, 1.05))
        now = time.time()
        ts = random.uniform(self.last_time, now)
        server = random.choice(server2asg.keys())
        cpu = random.uniform(*server_cpu[server2asg[server]])
        self._collector.emit(Values([ts, server, { "cpu": cpu }]))
        self.last_time = now

    def declareOutputFields(self, declarer):
        declarer.declare(Fields(["ts", "server", "payload"]))


class SchedulerSpout(BaseRichSpout):
    __proxymaker__ = ClampProxyMaker("otter")

    def open(self, conf, context, collector):
        self._collector = collector
        self.last_time = time.time()

    def nextTuple(self):
        time.sleep(random.uniform(5., 10.))
        now = time.time()
        ts = random.uniform(self.last_time, now)
        asg = random.choice(server2asg.values())
        self._collector.emit(Values([ts, None, { "request": random.choice([-1, 0, 1]) }, asg]))
        self.last_time = now

    def declareOutputFields(self, declarer):
        declarer.declare(Fields(["ts", "server", "payload", "asg"]))   # server will be None


class LookupASGBolt(BaseRichBolt):

    __proxymaker__ = ClampProxyMaker("otter")

    def prepare(self, conf, context, collector):
        self._collector = collector

    def execute(self, t):
        ts, server, payload = t.getValues()
        asg = lookup_asg(server)
        self._collector.emit(t, Values([ts, server, payload, asg]))
        self._collector.ack(t)

    def declareOutputFields(self, declarer):
        declarer.declare(Fields(["ts", "server", "payload", "asg"]))


class PolicyBolt(BaseRichBolt):

    # There must only be at most one instance per ASG; ensure by
    # configuring properly in the topology using FieldsGrouping.

    __proxymaker__ = ClampProxyMaker("otter")

    def prepare(self, conf, context, collector):
        self._collector = collector
        self.policies = defaultdict(partial(Policy, age=15.))  # keep aging low for now

    def execute(self, t):
        if is_tick_tuple(t):
            log.info("Deciding on the following policies: %s", self.policies.keys())
            for asg, policy in self.policies.iteritems():
                decision = policy.decide(asg)
                if decision:
                    self._collector.emit(t, Values([asg, decision]))  # this might cause too much herding... to be seen
                    policy.ack_decision()  # FIXME still need to consider transactional semantics
            self._collector.ack(t)
            return

        ts, server, payload, asg = t.getValues()  # FIXME type the tuple with some sort of prefix label?
        log.info("Observing on ts=%s, server=%s, asg=%s, payload=%s", ts, server, asg, payload)
        policy = self.policies[asg]
        if "request" in payload:
            policy.request(payload["request"])
        else:
            policy.observe(server, ts, payload["cpu"])
        self._collector.ack(t)

    def declareOutputFields(self, declarer):
        declarer.declare(Fields(["asg", "decision"]))

    def getComponentConfiguration(self):
        # Every 5 seconds, make a decision - this is sped up just because we're poor impatient humans
        return { Config.TOPOLOGY_TICK_TUPLE_FREQ_SECS: 5 }


class LogPolicyBolt(BaseRichBolt):

    __proxymaker__ = ClampProxyMaker("otter")

    def prepare(self, conf, context, collector):
        self._collector = collector

    def execute(self, t):
        log.info("Logging policy decision: %s", t.getValues())
        self._collector.ack(t)


def get_topology_builder():
    # NEXT UP: figure out how to do this in the context of trident or transactional topologies
    # in general. We know that's feasible, so just experiment for now without those types of guarantees.

    # May want some sort of health checker like this; depends on what MaaS can provide us
    # builder.setSpout("status-spout", JobStatusSpout(), 4)    # Not certain where this comes from - can we get it from MaaS too?

    # FIXME parallelism numbers are completely arbitrary! this function should take these as optional parameters;
    # however the parallelism is greater than 1 so we can see that proper isolation is being performed
    builder = TopologyBuilder();        
    builder.setSpout("maas-spout", MonitoringSpout(), 4)     # Read from Kafka the monitoring data. Or a file to simulate.
    builder.setSpout("scheduler-spout", SchedulerSpout(), 4) # Pull in scheduling policy
    builder.setBolt("lookup-asg-bolt", LookupASGBolt(), 2)\
           .shuffleGrouping("maas-spout")
    builder.setBolt("policy-bolt", PolicyBolt(), 4)\
           .fieldsGrouping("lookup-asg-bolt", Fields(["asg"]))\
           .fieldsGrouping("scheduler-spout", Fields(["asg"]))\
    # Write out policy decisions; FIXME at some point, call a webhook in otter
    builder.setBolt("log-policy", LogPolicyBolt()).globalGrouping("policy-bolt")
    return builder

    
