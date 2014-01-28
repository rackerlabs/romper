Status
======

This is a *spike* to learn Storm and how to integrate it with Jython
and other tech. For now, that means no testing and minimal docs.


Setup
=====

This will be replaced by a much better setup. But for now:

* You need Storm installed with its bin directory on `$PATH`.

* Use my branch of Jython that supports SSL. This branch is necessary
  in order to have setuptools support.

You can install this branch as follows:

````bash
$ hg clone https://bitbucket.org/jimbaker/jython-ssl
$ (cd jython=ssl && ant)                              # build development version (fastest way)
$ alias jython-ssl=$(pwd)/jython-ssl/dist/bin/jython
````

The romper package also depends on clamp, for Java <=> Python
integration. More details on clamp can be found in the [clamped
branch][], which goes into more details on how to use clamp.

You next need to build a single jar -- or uber jar -- for all of your
package dependencies. Note that running `storm classpath` computes the
necessary classpath for Storm dependencies, but you of course don't
need to include this in the single jar:

````bash
$ git clone https://github.com/jythontools/clamp.git
$ pushd clamp
$ jython-ssl setup.py install
$ popd
$ git clone https://github.com/rackerlabs/romper.git
$ pushd romper
$ jython-ssl setup.py install
$ CLASSPATH=$(storm classpath) jython-ssl setup.py clamp      # create proxy in site-packages
$ CLASSPATH=$(storm classpath) jython-ssl setup.py singlejar  # defaults to romper-0.1-single.jar
````

Next, run the topology. Choose standalone mode with `--local`. In both
cases, the cluster/standalone submitting code ("main") is in
`__run__.py` in the top level directory:

````bash
CLASSPATH="$(storm classpath):$(pwd)/romper-0.1-single.jar" java org.python.util.JarRunner --local
````

Or you can run on the storm cluster by submitting the uber jar to Nimbus:

````bash
$ storm jar romper-0.1-single.jar org.python.util.JarRunner
````

Various additional options are available. Use `--help`, or better yet,
read the code, since this is still very early stages.


<!-- references -->
  [clamped branch]: https://github.com/jimbaker/clamped
