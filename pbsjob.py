#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""Create jobscripts for the PBS scheduler and submit them on a given host
(typically the login node of a cluster).

The name of the login node is read from a plain text file (~/pbsjob.dat by
default). The working directory on the remote machine is also given in that
file. Furthermore, a suffix for jobscripts may as well be given. Modifictations
to the file's name and location have to be performed in the source code.

The script will copy the argument file to a temporary file in the remote's work
directory and generate a jobscript using information given as a command line
options. Finally, the jobscript will be submitted.

(c) 2012-2013 Alexander Eberspächer
"""

from optparse import OptionParser
import subprocess
import tempfile
import os
import sys

# parse command line options:
usage = "usage: %prog -n value -p value. Get help with --help."
parser = OptionParser(usage=usage, version="%prog 0.1")
parser.add_option("--nodes", action="store", dest="nodes", type="int",
                  help="Number of nodes.")
parser.add_option("--ppn", action="store", dest="ppn", type="int",
                  help="Number of processes per node.")
parser.add_option("--name", action="store", dest="name", type="string",
                  help="Job name.")
parser.add_option("--clean", action="store_true", dest="do_clean",
                  help="Clean jobscripts on the remote and quit.")
parser.add_option("--stdout", action="store", dest="std_out_file", type="string",
                  help="Write stdout to this file.")
parser.add_option("--stderr", action="store", dest="std_err_file", type="string",
                  help="Write stderr to this file.")
parser.add_option("--shared", action="store_true", default=False,
                  dest="shared", help="""Share the nodes.""")
parser.add_option("--walltime", action="store", default=100,
                  dest="walltime", help="""Walltime in hours.""")
parser.add_option("--queue", action="store", dest="queue", type="string",
                  default="parallel", help="Name of the queue to use.")
parser.add_option("--no_MPI", action="store_true", default=False,
                  dest="no_MPI", help="""Do not use MPI.""")
parser.add_option("--ncpus", action="store_true", default=False,
                  dest="num_cpus", help="""Include ncpus in jobscript.""")
parser.add_option("--priority", action="store", dest="priority", type="int",
                  default=0, help="Process priority.")
parser.add_option("--config", action="store", default=None,
                  dest="config_file", help="""Config file.""")
(options, args) = parser.parse_args()

# obtain login information from file:
if(options.config_file is None):
    settings_dir = os.environ["HOME"]
    settings_filename = "pbsjob.dat"
    if(not settings_dir.endswith('/')):
        settings_dir += "/"
    config_file = settings_dir+settings_filename
else:
    config_file = options.config_file

# The file shall contain the lines:
# user@login.machine.tld
# workingDirectoryOnRemoteMachine
if(not os.path.exists(config_file)):
    raise Exception("Could not open config file %s! Aborting!"%config_file[0])

fil = open(config_file, "r")

try:
    login = fil.readline().strip()
except:
    raise Exception("Could not read host from %s"%fil)

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

print("Working in %s:%s."%(login, workdir))

if(suffix == ""):
    suffix = ".jobscript"
    print("No suffix for jobscript given, using suffix %s instead."%suffix)

# TODO: try to remove that annoying code duplication above

fil.close()

devnull = open(os.devnull)  # used for output redirection

if(options.do_clean):  # *only* perform cleaning and then quit
    decision = raw_input("Remove *%s in %s:%s [y/n]? "%(suffix, login, workdir))
    if(decision in ["y", "yes", "Yes", "YES"]):
        errcode = subprocess.call("ssh %s rm %s/*%s"%(login, workdir.strip(), suffix),
                                  shell=True)
        if(errcode != 0):
            raise OSError("Deletion of jobscripts failed!")
    sys.exit(0)

# check if a script to execute was given:
if(len(args) == 0):
    parser.error("No script name given!")

# check if script exists:
if(not os.path.exists(args[0])):
    raise Exception("Script %s does not exist! Aborting!"%args[0])

# check if script is executable, fail otherwise:
if(not os.access(args[0], os.X_OK)):
    raise Exception("File %s is not executable! Aborting!"%args[0])

# prepare filename for copying:
file_basename = args[0].split("/")[-1]  # extract base name

# prepare job name:
if(not options.name):
    jobName = file_basename
    print("No job name given, using %s instead."%jobName)
else:
    jobName = options.name

# check if mandatory options are present:
if(not options.nodes):
    parser.error("Specify the number of nodes using the --nodes option!")
if(not options.ppn):
    parser.error("Specify the number of processes per nodes using the --ppn option!")

# generate input/output filenames if necessary:
if(not options.std_out_file):
    std_out_file = jobName+".out"
    print("No file for stdout given, will use %s instead."%std_out_file)
else:
    std_out_file = options.std_out_file
if(not options.std_err_file):
    std_err_file = jobName + ".err"
    print("No file for stderr given, will use %s instead."%std_err_file)
else:
    std_err_file = options.std_err_file

# check if an argument to execute is present:
if(len(args) == 0):
    parser.error("Specify a file to run with PBS!")

# now try to find out if the script/program to execute already exits in the
# remote directory - if so, prompt before it is overwritten
errcode = subprocess.call(["ssh", login, "ls", "%s/%s"%(workdir, file_basename)],
                          stdout=devnull, stderr=devnull)
doCopy = True  # assume a file has to be copied first
if(errcode == 0):  # file already exists, ask to overwrite
    decision = raw_input("The file %s already exists in the remote location!\nOverwrite [y/n]? Answering 'n' will use the remote file as is. "%args[0])

    if(decision in ["y", "Y", "yes", "Yes", "YES"]):
        doCopy = True
    else:
        doCopy = False
if(doCopy):
    errcode = subprocess.call("scp %s %s:%s"%(file_basename, login, workdir),
                              stdout=devnull, stderr=devnull, shell=True,
                              cwd=os.environ["PWD"])
    if(errcode != 0):
        raise OSError("Something went wrong copying the program to be executed! Aborting!")

# if option shared is used, prepare a suitable string for jobscript:
if(options.shared):
    shared_string = "#shared"
else:
    shared_string = ""

# in case --ncpus is used, prepare a suitable string for inclusion in jobscript:
if(options.num_cpus):
    num_cpu_string = "#PBS -l ncpus=%s"%(options.nodes*options.ppn)
else:
    num_cpu_string = ""

# prepare command to run in jobscript:
if(options.no_MPI):
    command = args[0]
else:
    command = "mpirun %s"%args[0]

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
%s
### Name of queue
#PBS -q %s
#PBS -p %s

echo $LD_LIBRARY_PATH
echo $PATH
. $HOME/.bashrc

echo Working directory $PBS_O_WORKDIR
cd $PBS_O_WORKDIR
echo "Host"
hostname

%s
"""%(jobName, std_out_file, std_err_file, options.nodes, options.ppn,
     shared_string, options.walltime, num_cpu_string, options.queue, options.priority,
     command)

# write jobscript to a temporary file:
jobFile = tempfile.NamedTemporaryFile(suffix=suffix, dir="")
jobFile.write(jobscript)
jobFile.flush()

# scp the jobscript to the remote:
print("Copy jobscript to %s:%s"%(login, workdir))
errcode = subprocess.call(["scp", jobFile.name, "%s:%s"%(login, workdir)],
                          stdout=devnull, stderr=devnull)
if(errcode != 0):
    raise OSError("Copying the jobscript failed, aborting!")

# now, qsub the jobscript:
job_script_basename = jobFile.name.split("/")[-1]
errcode = subprocess.call(["ssh",
                           login,
                           "cd %s; qsub %s"%(workdir, job_script_basename)
                           ])
if(errcode != 0):
    raise Exception("Something went wrong submitting the job! Aborting!")
else:
    print("Job submitted, using %s CPUs in total."%(options.nodes*options.ppn))

# TODO: figure out how to run hybrid OpenMP/MPI jobs
