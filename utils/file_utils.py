# -*- coding: utf-8 -*-

import logging
import os

import yaml

logger = logging.getLogger(__name__)


def read_yaml(config_path, config_name=''):
    if config_path and os.access(config_path, os.F_OK):
        with open(config_path, 'r', encoding="utf-8") as f:
            conf = yaml.safe_load(f.read())
        if not config_name:
            return conf
        elif config_name in conf.keys():
            return conf[config_name.upper()]
        else:
            raise KeyError('Configuration information was not found')
    else:
        raise ValueError('The file does not exist')
