#!/usr/bin/env python
#-*- coding:utf-8 -*-

from mpi4py import MPI
import sys

MPIroot = 0 # define the root process
MPIcomm = MPI.COMM_WORLD # MPI communicator

# get rank (= number of individual process) and
# size (= total number of processes)
MPIrank, MPIsize = MPIcomm.Get_rank(), MPIcomm.Get_size()

print("Howdy from process %s of %s"%(MPIrank, MPIsize))
print >> sys.stderr, "This is an error just for testing."
