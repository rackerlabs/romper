import argparse

from backtype.storm import Config, LocalCluster, StormSubmitter
from romper.topology import get_topology_builder


def main(run_local=False):
    parser = argparse.ArgumentParser(description="Generate a single jar for Storm")
    parser.add_argument("--local", default=run_local, action="store_true", help="Run topology in a local cluster")
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debug logging")
    parser.add_argument("--num-workers",default=2, type=int, help="Number of workers")
    parser.add_argument("--name", default="romper", help="Topology name")
    args = parser.parse_args()

    conf = Config()
    conf.setDebug(args.debug)
    conf.setNumWorkers(args.num_workers)

    cluster = LocalCluster() if args.local else StormSubmitter
    builder = get_topology_builder()
    cluster.submitTopology(args.name, conf, builder.createTopology())


print "Running under", __name__
main(run_local=__name__ == "__main__")
