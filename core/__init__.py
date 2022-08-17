# -*- coding: utf-8 -*-

import logging
import logging.config
import os
from pathlib import Path

from utils.file_utils import read_yaml
from .constant import DEFAULT_CONFIG_PATH, DEFAULT_FIELD_STYLES
from .context import Context
from .dispatch import Dispatcher


def create_ctx(config_path=None, config_env='DEVELOPMENT'):
    if not (config_path and os.access(config_path, os.F_OK)):
        for path in DEFAULT_CONFIG_PATH:
            if os.access(path, os.F_OK):
                config_path = path
                break

    ctx = Context(config_path, config_env)

    ctx.logger = logging.getLogger(__name__)
    log_config_path = str(Path.cwd().joinpath('config').joinpath('logging.yaml'))
    log_config_dict = read_yaml(log_config_path)
    if not os.path.exists("log"):
        os.makedirs("log")
    log_config_dict['handlers']['console']['level'] = 'DEBUG' if Context.CONF[
                                                                     'DEBUG'] or config_env == 'DEVELOPMENT' else 'INFO'
    log_config_dict['handlers'].pop('file_handler')
    logging.config.dictConfig(log_config_dict)
    import coloredlogs
    coloredlogs.DEFAULT_FIELD_STYLES = DEFAULT_FIELD_STYLES
    coloredlogs.install(fmt=log_config_dict['formatters']['simple']['format'], level=ctx.logger.level,
                        logger=ctx.logger)

    ctx.logger.info('Operating environment: {}'.format(config_env))
    ctx.logger.info('Using config path: {}'.format(config_path))

    ctx.register_mq(Dispatcher.handle_msg)
    ctx.register_coroutine()

    return ctx
