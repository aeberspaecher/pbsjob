#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""Create jobscripts for the PBS scheduler and submit them on a given host
(typically the login node of a cluster).

The name of the login node is read from a plain text file (~/pbsjob.dat).
The working directory on the remote machine is also given in that file.
Furthermore, a suffix for jobscripts may as well be given.
Modifictations to the file's name and location have to be performed in the
source code.

The script will copy the argument file to a temporary file in the remote's
work directory and generate a jobscript using information given as a command
line options. Finally, the jobscript will be submitted.

(c) 2012 Alexander Eberspächer
"""

from optparse import OptionParser
from subprocess import Popen
import subprocess
import tempfile
import os, sys

# parse command line options:
usage = "usage: %prog -n value -p value. Get help with --help."
parser = OptionParser(usage=usage, version="%prog 0.1")
parser.add_option("-n", "--nodes", action="store", dest="nodes", type="int",
                  help="Number of nodes.")
parser.add_option("-p", "--ppn", action="store", dest="ppn", type="int",
                  help="Number of processes per node.")
parser.add_option("-a", "--name", action="store", dest="name", type="string",
                  help="Job name.")
parser.add_option("-o", "--stdout", action="store", dest="stdoutFile", type="string",
                  help="Write stdout to this file.")
parser.add_option("-e", "--stderr", action="store", dest="stderrFile", type="string",
                  help="Write stderr to this file.")
parser.add_option("-s", "--shared", action="store_true", default=False,
                  dest="shared", help="""Share the nodes.""")
parser.add_option("-w", "--walltime", action="store", default=800,
                  dest="walltime", help="""Walltime in hours.""")
(options, args) = parser.parse_args()

if(not options.nodes):
    parser.error("Specify the number of nodes using the -n option!")
if(not options.ppn):
    parser.error("Specify the number of processes per nodes using the -p option!")
if(not options.name):
    print("No job name given, will use the filename instead.")

if(len(args) == 0):
    parser.error("Specify a file to run with PBS!")

# obtain login information from file:
settingsDirectory = os.environ["HOME"]
settingsFileName = "pbsjob.dat"
# The file shall contain the line: user@login.machine.tld
try:
    if(settingsDirectory[-1] != "/"):
        settingsDirectory += "/"
    fil = open(settingsDirectory+settingsFileName)
except:
    print >> sys.stderr, "Could not open settings file!"
    sys.exit(1)

try:
    login = fil.readline().strip()
except:
    print >> sys.stderr, "Could not read host from %s"%fil

try:
    workdir = fil.readline().strip()
except:
    workdir = os.environ["PWD"]
    print("No working directory specified, using %s instead."%workdir)

try:
    suffix = fil.readline().strip()
except:
    suffix = ".jobscript"
    print("No suffix for jobscript given, using suffix %s instead."%suffix)

# catch the case of workdir being an empty line (may happen with text
# editors that automatically append a new line at the end of each file)
if(workdir == ""):
    workdir = os.environ["PWD"]
    print("No working directory specified, using %s instead."%workdir)

if(suffix == ""):
    suffix = ".jobscript"
    print("No suffix for jobscript given, using suffix %s instead."%suffix)

# TODO: try to remove that annoying code duplication above

fil.close()

if(not options.name):
    jobName = args[0]
else:
    jobName = options.name

# generate additional filenames if necessary:
if(not options.stdoutFile):
    stdoutFile = jobName+".out"
    print("No file for stdout given, will use %s instead."%stdoutFile)
else:
    stdoutFile = options.stdoutFile
if(not options.stderrFile):
    stderrFile = jobName+".err"
    print("No file for stderr given, will use %s instead."%stderrFile)
else:
    stderrFile = options.stderrFile

if(options.shared): # if shared is used, prepare a suitable string for jobscript
    sharedString = "#shared"
else:
    sharedString = ""

# now try to find out if the script/program to execute already exits in the
# remote directory - if so, prompt before it is overwritten
devnull = open(os.devnull) # also used later!
errcode = subprocess.call(["ssh", login, "ls", "%s/%s"%(workdir, args[0])],
                          stdout=devnull, stderr=devnull)

doCopy = True # assume a file has to be copied first
if(errcode == 0): # file already exists, ask to overwrite
    decision = raw_input("The file %s already exists in the remote location!\nOverwrite [y/n]? Answering 'n' will use the remote file as is. "%args[0])

    if(decision in ["y", "Y", "yes", "Yes", "YES"]):
        doCopy = True
    else:
        doCopy = False


if(doCopy):
    errcode = subprocess.call(["scp", args[0], "%s:%s"%(login,workdir)],
                      stdout=devnull, stderr=devnull)
    if(errcode != 0):
        print("Something went wrong copying the program to be executed! Aborting!")
        sys.exit(1)
    

# now generate a jobscript:
# We assume OpenMPI in recent versions - in these versions, it is unnecessary
# to specify the hostnames and number of processes
jobscript = \
r"""#!/bin/sh
### Job name
#PBS -N %s
### Output files
#PBS -o %s
#PBS -e %s
### Number of nodes, PPN, shared
#PBS -l nodes=%s:ppn=%s%s
#PBS -l walltime=%s:00:00

. $HOME/.bashrc

echo Working directory $PBS_O_WORKDIR
cd $PBS_O_WORKDIR
echo "Host"
hostname

mpirun %s
"""\
%(jobName, stdoutFile, stderrFile, options.nodes, options.ppn,
  sharedString, options.walltime, args[0])

# write jobscript to a temporary file:
jobFile = tempfile.NamedTemporaryFile(suffix=suffix, dir="")
jobFile.write(jobscript)
jobFile.flush()

# scp the jobscript to the remote
print("Copy jobscript to %s:%s"%(login, workdir))
errcode = subprocess.call(["scp", "%s"%jobFile.name, "%s:%s"%(login, workdir)],
                stdout=devnull, stderr=devnull)
if(errcode != 0):
    print("Copying the jobscript failed, aborting!")
    sys.exit(1)

# now, qsub the jobscript
errcode = subprocess.call(["ssh", login, "cd %s; qsub %s"
                          %(workdir, jobFile.name.split("/")[-1])])
                          # extract jobscript file's basename
if(errcode != 0):
    print("Something went wrong submitting the jobscript! Aborting!")
else:
    print("Job submitted, using %s CPUs in total."%(options.nodes*options.ppn))
