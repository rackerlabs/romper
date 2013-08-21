Support AtomSpout scaling
=========================

Need to consistently hash each url to the group. Start with existing Python support for this in PyPI, but we need to also determine for each instance of the AtomSpout its placement in the topology.

Start here:
http://nathanmarz.github.io/storm/doc/backtype/storm/task/TopologyContext.html

Determine pool:
TopologyContext#getComponentTasks(TopologyContext#getThisComponentId)

Determine entry in the pool:
TopologyContext#getThisTaskId

Potentially use this in some way; in particular if this changes we know this may require rebalancing
so as to not lose entries:
TopologyContext#getThisTaskIndex