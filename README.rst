======
pbsjob
======

About
=====

``pbsjob`` is a dirty little script useful in the submission of jobs to
clusters running the PBS scheduler. It was made to submit jobs from a
workstation without being required to remember how to write jobscripts.

Typical use case
================

You keep your shared objects/libraries and helper tools in ``~/someFolder``.
On the login node of your cluster, you have the same tools in
``~/remoteFolder``. You want to run scripts in these folders.

You find yourself copying the script to the cluster, logging into the
cluster, writing a jobscript, submitting the jobscript and logging off
again. This lengthy procedure is shortenend with this script.

Usage
=====

Configuration
-------------

The script reads ``~/pbsjob.dat`` on your local machine. The file shall contain
your username and the URL for the remote machine, the working directory on the
login node as well as a suffix for jobscript filenames. An example is given
here::

  user@machine.domain
  remoteFolder
  .jobscript

Submitting scripts
------------------

Type

::

  pbsjob.py --nodes 2 --ppn 8 --name MyName --stdout bla.out
      --stderr bla.err --walltime 2 --queue queueName
      --priority 23 ./scriptToRun

to submit the file ``./scriptToRun`` to the remote machine given in the
configuration file. The job will use 2 nodes with 8 processes per node,
standard output is written to ``bla.out`` in the working directory, standard
error is written to ``bla.err`` respectively. The walltime will be 2 hours.
The job's name will be "MyName". The queue "queueName" will be used and the
job's priority will be 23.

If the file "scriptToRun" already exists on the remote, you are asked whether
you want to overwrite the remote file or use the existing file.

The arguments ``--name``, ``--queue``, ``--walltime``, ``--stdout`` and
``--stderr``, ``--priority`` are optional:

- If ``--name jobName`` is not given, the script's name is used as the job
  name, too.
- If  ``--walltime wallTimeInHours`` is not given, the walltime defaults to
  100 hours.
- If ``--stdout fileForStdout`` or ``--stderr fileForStderr`` are not given,
  the output files default to the job name suffixed by ".out" and ".err",
  respectively.
- If ``--queue queueName`` is not given, the default queue will be "parallel".
- If ``--priority number`` is not given, the job priority defaults to 0.

By using all default arguments, the shortest allowed call is

::

  pbsjob.py --nodes 1 --ppn 2 ./script

You can get help by typing

::

  ./pbsjob.py --help

Additional options
------------------

- The ``--clean`` option deletes all remote files suffixed by the string
  given in the configuration file, i.e.

  ::

    pbsjob.py --clean

  with the example ``pbsjob.dat`` given above issues the command

  ::

    ssh user@machine.domain rm remoteFolder/*.jobscript

  Nothing else will be done.

- If the option ``--nompi`` is used, the submitted script will *not* be run
  after a ``mpirun`` command. This might help for OpenMP jobs.

- If ``--ncpus`` is present, the script will include the PBS ncpus option
  with the value nodes*(processes per node). This seems to be necessary on
  the author's cluster in some cases.

Pitfalls
--------

The script tries to transfer the script to run to the remote machine. This
may cause you trouble in case you don't want a script to be transfered, but
you rather want a composite command such as

::

  time python myScript.py

to be execute on the remote. In this case, you cannot use ``pbsjob.py``
without wrapping your command in a shell script.

Also you may want to be careful with executable files compiled on your local
machine - they may not be able to run on the remote architecture.

Modifications
=============

To use different schedulers, you may want to modify the part of the source
that sets the ``jobscript`` variable. Also, default names and conventions
can be found in the source.
