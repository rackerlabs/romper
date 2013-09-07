Status
======

This is a *spike* to learn Storm and how to integrate it with Jython and other tech. For now, that means no testing
and minimal docs.


Setup
=====

This will be replaced by a much better setup. But for now:

You need Storm installed with its bin directory on `$PATH`.

Checkout Jython trunk and build it. It includes a necessary fix for using Jython with Clojure types as well as new custom proxy maker support for better Java integration.


~~~~
$ hg clone http://hg.python.org/jython jython27
$ cd jython27 
$ ant                                                 # build development version (fastest way)
$ export PATH=$(pwd)/dist/bin:$PATH                   # add jython to your path; I sometimes alias to jython27 to be clear
~~~~

This package also includes a very preliminary and ultra simplistic implementation of clamp for Java <=> Python integration, similar to what is discussed here: http://darjus.blogspot.com/2013/01/customizing-jython-proxymaker.html. One key difference: this version is written in pure Jython (that is, only Python, importing standard Java libraries, but otherwise not in Java).

Two more steps:

1. Build an "uber" jar file for Storm; this contains all necessary jars. Running `storm classpath` computes the necessary classpath for Storm dependencies:

~~~~
CLASSPATH="$(storm classpath)" jython gen-storm-jar.py -o uber.jar -i romper -i clamp --proxy=romper.topology
~~~~

2. Run the topology. Choose standalone mode with `--local`. In both cases, the cluster/standalone submitting code ("main") is in `__run__.py`:

~~~~
CLASSPATH="$(storm classpath):$(pwd)/uber.jar" java org.python.util.JarRunner --local
~~~~

or on the storm cluster by submitting the uber jar:

~~~~
$ storm jar uber.jar org.python.util.JarRunner
~~~~

Various additional options are available. At some point `--help` will be fixed :), until then read the code.





