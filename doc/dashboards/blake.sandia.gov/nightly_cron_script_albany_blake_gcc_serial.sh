#!/bin/csh

BASE_DIR=/home/projects/albany/nightlyCDashAlbanyBlake
cd $BASE_DIR

rm -rf build-gcc
rm -rf repos-gcc
rm -rf nightly*Gcc*.txt
rm -rf gcc_modules.out 

unset http_proxy
unset https_proxy

source blake_gcc_modules_submit.sh >& gcc_modules.out

export OMP_NUM_THREADS=1

LOG_FILE=$BASE_DIR/nightly_log_blakeAlbanyGccSerial.txt

eval "env  TEST_DIRECTORY=$BASE_DIR SCRIPT_DIRECTORY=$BASE_DIR ctest -VV -S $BASE_DIR/ctest_nightly_albany_gcc_serial.cmake" > $LOG_FILE 2>&1

