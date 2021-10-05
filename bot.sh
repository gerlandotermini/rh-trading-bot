#!/bin/sh
# Start/Stop script for Robinhood Bot
#

BOTPID=`ps -ef | grep '/usr/bin/python[3] -u ./core.py' | awk '{ print $2 }'`

start() {
    if [ -z "$BOTPID" ]; then
        /usr/bin/nohup ./core.py > status.log 2>&1 &
        sleep 3
        BOTPID=`ps -ef | grep '/usr/bin/python[3] -u ./core.py' | awk '{ print $2 }'`
        if [ -z "$BOTPID" ]; then
            echo "Unable to start bot."
        else
            echo "[PID:$BOTPID] Bot started."
        fi
    else
        echo "Bot already running. Did you mean 'restart'?"
    fi
}
 
stop() {
    if [ -z "$BOTPID" ]; then
        echo "Bot not running."
    else
        kill $BOTPID
        sleep 3
        echo "[PID:$BOTPID] Bot stopped."
        BOTPID=`ps -ef | grep '/usr/bin/python[3] -u ./core.py' | awk '{ print $2 }'`
    fi
}

status() {
    if [ -z "$BOTPID" ]; then
        echo "Bot not running."
    else
        echo "[PID:$BOTPID] Bot running."
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop   
        ;;
    restart)
        stop
        start
        ;;
    status)
        status
        ;;
    *)
    echo "Usage: service {start|stop|restart|status}"
    exit 1
esac
exit 0