#!/bin/bash

PIDFILE=run.py.pid

case $1 in
  start)
    ##check if pid exists and matches a running process
    if [ -f $PIDFILE ]
    then
      PID=$(cat $PIDFILE)
      ps -p $PID > /dev/null 2>&1
      if [ $? -eq 0 ]
      then
        echo "Process already running as $PID with PID file $PIDFILE"
        exit 1
      else
        ## Process not found assume not running
        echo "Removing orphaned PID file $PIDFILE"
        rm $PIDFILE
      fi
    fi



    nohup python3 run.py 2>&1 >run.py.log </dev/null & echo $! > $PIDFILE
    exit 0
  ;;
  stop)
    ##check if pid exists and matches a running process
    if [ -f $PIDFILE ]
    then
      PID=$(cat $PIDFILE)
      ps -p $PID > /dev/null 2>&1
      if [ $? -eq 0 ]
      then
          echo "Terminating process $PID"
          kill $PID
          sleep 30
          ps -p $PID > /dev/null 2>&1
        if [ $? -eq 0 ]
        then
          echo "Force-terminating process $PID"
            kill -9 $PID
        fi
        rm $PIDFILE
        exit 0
      else
          echo "Process $PID not running, deleting $PIDFILE"
        rm $PIDFILE
        exit 0
      fi
    else
      echo "Unable to find $PIDFILE to terminate process"
      exit 2 
    fi
  ;;
esac