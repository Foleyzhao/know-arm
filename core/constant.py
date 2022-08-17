# -*- coding: utf-8 -*-

from pathlib import Path

DEFAULT_CONFIG_PATH = ['/etc/know-arm/config.yaml', Path.cwd().joinpath('config').joinpath('config.yaml')]

DEFAULT_FIELD_STYLES = {
    'asctime': {'color': 'green'},
    'hostname': {'color': 'magenta'},
    'levelname': {'color': 'green', 'bold': True},
    'request_id': {'color': 'yellow'},
    'name': {'color': 'white'},
    'programname': {'color': 'cyan'},
    'threadName': {'color': 'yellow'}
}

MAX_WORKER = 5
