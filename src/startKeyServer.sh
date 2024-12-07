#!/usr/bin/env bash
CURRENT_DIR=$(python3 -c "import os; print(os.path.realpath('$1'))")
BASE_DIR="$(dirname "$CURRENT_DIR")"
CERT_PATH="$BASE_DIR/data/certs/"
export FLASK_APP=key_server
export LANG=C.UTF-8
python3 -m flask run --host=0.0.0.0 --port=5000 --cert="${CERT_PATH}keyserver.crt" --key="${CERT_PATH}keyserver.key"