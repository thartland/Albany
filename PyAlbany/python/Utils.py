"""@package docstring
Documentation for the PyAlbany.Utils module.

This module provides utility functions for the Python wrapper of Albany (wpyalbany).
"""

from PyAlbany import Albany_Pybind11 as wpa
import numpy as np
import sys

def createMultiVector(map, n):
    return wpa.RCPPyMultiVector(map, n, True)

def createVector(map):
    return wpa.RCPPyVector(map, True)

def norm(distributedVector):
    """@brief Computes the norm-2 of a distributed vector using Python and Teuchos MPI communicator."""
    return np.sqrt(inner(distributedVector, distributedVector))

def inner(distributedVector1, distributedVector2):
    """@brief Computes the l2 inner product of two distributed vectors using Python and Teuchos MPI communicator."""
    return distributedVector1.dot(distributedVector2)

def innerMVector(distributedMVector1, distributedMVector2):
    """@brief computes C = A^T B, where A is a n x r1 MultiVector and B is a n x r2 MultiVector using Python and Teuchos MPI communicator."""
    r1 = distributedMVector1.getNumVectors()
    r2 = distributedMVector2.getNumVectors()
    C    = np.zeros((r1, r2))
    for i in range(r1):
        for j in range(r2):
            C[i, j] = inner(distributedMVector1.getVector(i), distributedMVector2.getVector(j))
    return C

def innerMVectorMat(distributedMVector, array):
    """@brief computes C = A B, where A is an n x r1 MultiVector, B is a nondistributed r1 x r2 array and C is a n x r2 MultiVector"""
    r1 = distributedMVector.getNumVectors()
    r2 = array.shape[1]
    C = createMultiVector(distributedMVector.getMap(), r2)
    C_view = C.getLocalViewHost()
    distributedMVector_view = distributedMVector.getLocalViewHost()

    for k in range(r1):
        for i in range(r2):
            C_view[:,i] += array[k, i] * distributedMVector_view[:,k]
    C.setLocalViewHost(C_view)
    return C 

def getDefaultComm():
    from mpi4py import MPI
    return wpa.getTeuchosComm(MPI.COMM_WORLD)

def createDefaultParallelEnv(comm = getDefaultComm(), n_threads=-1,n_numa=-1,device_id=-1):
    """@brief Creates a default parallel environment.
    
    This function initializes Kokkos; Kokkos will be finalized when the destructor of the returned ParallelEnv 
    object is called.
    """
    return wpa.PyParallelEnv(comm,n_threads,n_numa,device_id)

def createAlbanyProblem(filename, parallelEnv):
    """@brief Creates an Albany problem given a yaml file and a parallel environment."""
    return wpa.PyProblem(filename, parallelEnv)

def createParameterList(filename, parallelEnv):
    """@brief Creates a parameter list from a file."""
    return wpa.getParameterList(filename, parallelEnv)

def createEmptyParameterList():
    """@brief Creates an empty parameter list."""
    return wpa.RCPPyParameterList()

def writeParameterList(filename, parameterList):
    """@brief Writes a parameter list to a file."""
    wpa.writeParameterList(filename, parameterList)

def loadMVector(filename, n_cols, map, distributedFile = True, useBinary = True, readOnRankZero = True, dtype="d"):
    """@brief Loads distributed a multivector stored using numpy format.
    
    \param filename [in] Base name of the file(s) to load.
    \param n_cols [in] Number of columns of the multivector.
    \param map [in] Tpetra map of the multivector which has to be loaded.
    \param distributedFile (default: True) [in] Bool which specifies whether each MPI process reads a different
    file (if distributedFile==True, MPI process i reads filename+"_"+str(i)) or if all the entries are stored inside
    a unique file.
    \param useBinary (default: True) [in] Bool which specifies if the function reads a binary or a text file.
    \param readOnRankZero (default: True) [in] Bool which specifies if the file is read by the rank 0 and scattered or if
    it is read by all the MPI processes.
    \param dtype (default: "d") [in] Data type of the entries of the multivector.
    """
    rank = map.getComm().getRank()
    nproc = map.getComm().getSize()
    mvector = createMultiVector(map, n_cols)
    if nproc==1:
        if useBinary:
            mVectorNP = np.load(filename+'.npy')
        else:
            mVectorNP = np.loadtxt(filename+'.txt')

        mvector_view = mvector.getLocalViewHost()
        if(mVectorNP.ndim == 1 and n_cols == 1):
            mvector_view[:,0] = mVectorNP
        else: 
            for i in range(0, n_cols):
                mvector_view[:,i] = mVectorNP[i,:]
        mvector.setLocalViewHost(mvector_view)

    elif distributedFile:
        if useBinary:
            mVectorNP = np.load(filename+'_'+str(rank)+'.npy')
        else:
            mVectorNP = np.loadtxt(filename+'_'+str(rank)+'.txt')
        mvector_view = mvector.getLocalViewHost()
        for i in range(0, n_cols):
            mvector_view[:,i] = mVectorNP[i,:]
        mvector.setLocalViewHost(mvector_view)
    else:
        if readOnRankZero:
            map0 = wpa.getRankZeroMap(map)
            mvector0 = createMultiVector(map0, n_cols)
            if rank == 0:
                if useBinary:
                    mVectorNP = np.load(filename+'.npy')
                else:
                    mVectorNP = np.loadtxt(filename+'.txt')

                mvector0_view = mvector0.getLocalViewHost()
                if(mVectorNP.ndim == 1 and n_cols == 1):
                    mvector0_view[:,0] = mVectorNP
                else: 
                    for i in range(0, n_cols):
                        mvector0_view[:,i] = mVectorNP[i,:]
                mvector0.setLocalViewHost(mvector0_view)
            mvector = wpa.scatterMVector(mvector0, map)
        else:
            if useBinary:
                mVectorNP = np.load(filename+'.npy')
            else:
                mVectorNP = np.loadtxt(filename+'.txt')
            mvector_view = mvector.getLocalViewHost()
            for lid in range(0, map.getLocalNumElements()):
                gid = map.getGlobalElement(lid)
                mvector_view[lid,:] = mVectorNP[:,gid]
            mvector.setLocalViewHost(mvector_view)
    return mvector

def writeMVector(filename, mvector, distributedFile = True, useBinary = True):
    """@brief Loads distributed a multivector stored using numpy format.
    
    \param filename [in] Base name of the file(s) to write to.
    \param mvector [in] Distributed multivector to write on the disk.
    \param map [in] Tpetra map of the multivector which has to be loaded.
    \param distributedFile (default: True) [in] Bool which specifies whether each MPI process writes to a different
    file (if distributedFile==True, MPI process i writes filename+"_"+str(i)) or if all the entries are stored inside
    a unique file.
    \param useBinary (default: True) [in] Bool which specifies if the function writes a binary or a text file.
    """    
    rank = mvector.getMap().getComm().getRank()
    nproc = mvector.getMap().getComm().getSize()
    mvector_view = mvector.getLocalViewHost()
    if distributedFile:
        if useBinary:
            if nproc > 1:
                np.save(filename+'_'+str(rank)+'.npy', mvector_view.transpose())
            else:
                np.save(filename+'.npy', mvector_view.transpose())
        else:
            if nproc > 1:
                np.savetxt(filename+'_'+str(rank)+'.txt', mvector_view.transpose())
            else:
                np.savetxt(filename+'.txt', mvector_view.transpose())
    else:
        if nproc > 1:
            mvectorRank0 = wpa.gatherMVector(mvector, mvector.getMap())
        else:
            mvectorRank0 = mvector
        mvectorRank0_view = mvectorRank0.getLocalViewHost()
        if rank == 0:
            if useBinary:
                np.save(filename+'.npy', mvectorRank0_view.transpose())
            else:
                np.savetxt(filename+'.txt', mvectorRank0_view.transpose())

def createTimers(names):
    """@brief Creates Teuchos timers."""
    timers_list = []
    for name in names:
        timers_list.append(wpa.Time(name))
    return timers_list

def printTimers(timers_list, filename=None, verbose=True):
    """@brief Print Teuchos timers."""
    original_stdout = sys.stdout
    if filename is not None:
        f = open(filename, 'w')
        sys.stdout = f
    if verbose:
        print("Timers:")
    for timer in timers_list:
        if verbose:
            print(timer.name() +": "+str(timer.totalElapsedTime())+" seconds")
        else:
            print(timer.totalElapsedTime())
    sys.stdout = original_stdout
