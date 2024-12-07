#!/usr/bin/env bash
CURRENT_DIR=$(python3 -c "import os; print(os.path.realpath('$1'))")
BASE_DIR="$(dirname "$CURRENT_DIR")"
CERT_PATH="$BASE_DIR/data/certs/"
export FLASK_APP=map_server
export LANG=C.UTF-8
python3 -m flask run --host=0.0.0.0 --port=5001 --cert="${CERT_PATH}mapserver.crt" --key="${CERT_PATH}mapserver.key"