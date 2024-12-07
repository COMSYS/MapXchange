#!/usr/bin/env bash
CURRENT_DIR=$(python3 -c "import os; print(os.path.realpath('$0'))")
BASE_DIR="$(dirname "$CURRENT_DIR")"
BASE_DIR="$(dirname "$BASE_DIR")"
SESSION_NAME='Server'
if [ $# -ge 1 ]; then
    SESSION_NAME=$1
fi
cd $BASE_DIR/src || exit
tmux new-session -d -s $SESSION_NAME -n 'Key Server'
tmux send-keys -t $SESSION_NAME:0 './startKeyServer.sh' 'C-m'
tmux new-window -t $SESSION_NAME:1 -n 'Map Server'
tmux send-keys -t $SESSION_NAME:1 './startMapServer.sh' 'C-m'
tmux new-window -t $SESSION_NAME:2 -n 'User'