from mpi4py import MPI
import numpy as np
from PyAlbany import Utils
from PyAlbany import FEM_postprocess as fp
import os
import sys

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt


def run_forward(nSweeps, damping, parallelEnv):
    timerName = "PyAlbany Total Time@PyAlbany: performSolve@Piro::NOXSolver::evalModelImpl::solve@Thyra::NOXNonlinearSolver::solve@NOX Total Linear Solve"
    filename = "input.yaml"

    parameter = Utils.createParameterList(
        filename, parallelEnv
    )
    ifpack2 = parameter.sublist('Piro').sublist('NOX').sublist('Direction').sublist('Newton').sublist('Stratimikos Linear Solver').sublist('Stratimikos').sublist('Preconditioner Types').sublist('Ifpack2').sublist('Ifpack2 Settings')
    ifpack2.set('relaxation: sweeps', int(nSweeps))
    ifpack2.set('relaxation: damping factor', damping)

    problem = Utils.createAlbanyProblem(parameter, parallelEnv)
    problem.performSolve()

    return problem.getStackedTimer().baseTimerAccumulatedTime(timerName)


def main(parallelEnv):
    myGlobalRank = MPI.COMM_WORLD.rank

    nMaxSweeps = 300

    sweeps = np.arange(1, 6)
    dampings = np.linspace(0.8, 1.2, 21)

    N_sweeps = len(sweeps)
    N_dampings = len(dampings)
    N_measures = 100

    timers_sec = np.zeros((N_sweeps, N_dampings, N_measures))
    timers_mean_sec = np.zeros((N_sweeps, N_dampings))

    for i_sweeps in range(0, N_sweeps):
        for i_dampings in range(0, N_dampings):
            for i_measures in range(0, N_measures):
                timers_sec[i_sweeps, i_dampings, i_measures] = run_forward(sweeps[i_sweeps], dampings[i_dampings], parallelEnv)
            timers_mean_sec[i_sweeps, i_dampings] = np.median(timers_sec[i_sweeps, i_dampings, :])

    if myGlobalRank==0:
        np.savetxt('timers_sec.txt', timers_mean_sec)
        fig = plt.figure(figsize=(6,4))
        for i_dampings in range(0, N_dampings):
            plt.plot(sweeps, timers_mean_sec[:,i_dampings], 'o--', label='damping factor = ' + str(dampings[i_dampings]))
        plt.ylabel('Wall-clock time [sec]')
        plt.xlabel('Number of sweeps of the Gauss-Seidel preconditioner')
        plt.grid(True)
        plt.gca().set_xlim([np.amin(sweeps), np.amax(sweeps)])
        plt.legend()
        plt.savefig('nsweeps.jpeg', dpi=800)

        fig = plt.figure(figsize=(6,4))
        for i_sweeps in range(0, N_sweeps):
            plt.semilogy(dampings, timers_mean_sec[i_sweeps,:], 'o-', label='number of sweeps = ' + str(sweeps[i_sweeps]))
        plt.ylabel('Wall-clock time [sec]')
        plt.xlabel('Damping factor')
        plt.grid(True)
        plt.gca().set_xlim([np.amin(dampings), np.amax(dampings)])
        plt.gca().set_ylim([5e-3, 2e-2])
        plt.legend()
        fig.tight_layout()
        plt.savefig('damping.jpeg', dpi=800)

if __name__ == "__main__":
    parallelEnv = Utils.createDefaultParallelEnv()
    main(parallelEnv)
