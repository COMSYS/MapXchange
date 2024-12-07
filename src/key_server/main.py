"""
Blueprint for main pages of key server

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
import os
from typing import Any

from flask import (Blueprint, render_template, current_app,
                   send_from_directory)


log: logging.Logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)


@bp.route('/favicon.ico')
def favicon() -> Any:
    """Return key server favicon."""
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft'
                                                       '.icon')

@bp.route('/')
def main() -> str:
    """Load main page."""
    return render_template('base.html')
