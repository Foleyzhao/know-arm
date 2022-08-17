# -*- coding: utf-8 -*-

import sys

from utils.file_utils import read_yaml


class Context:
    CONF: dict = None
    CTX = None

    def __init__(self, config_path, config_env='DEVELOPMENT'):
        if not Context.CTX:
            Context.CTX = self
            if not Context.CONF:
                Context.CONF = read_yaml(config_path, config_env)

        self.env = config_env
        self.logger = None
        self.broker = None
        self.mq = None
        self.mq_is_running = False
        self.coroutine = None

    def register_mq(self, callback):
        from core import rabbitmq
        self.broker = rabbitmq.Broker()
        assert 'MQ_CONFIG' in self.CONF
        self.broker.load(config_dict=self.CONF['MQ_CONFIG'])
        self.mq = rabbitmq.RabbitMQ(self.broker, cb=callback)

    def register_coroutine(self):
        from core import coro
        attr = self.CONF['COROUTINE_CONFIG'] if 'COROUTINE_CONFIG' in self.CONF else {}
        self.coroutine = coro.Coro(daemon=True, **attr)
        self.coroutine.start()

    @property
    def version(self):
        return self.CONF["VERSION"]

    @property
    def mq_config(self):
        return self.CONF['MQ_CONFIG']

    def run(self):
        try:
            self.mq_is_running = True
            self.logger.info('Starting mq service')
            self.mq.run(thread=False, tag_prefix=self.mq_config['tag'] if 'tag' in self.mq_config else 'Know-arm',
                        no_ack=True)
        except KeyboardInterrupt:
            self.logger.info('Stopping Know-arm run and exiting...')
            sys.exit()
        except Exception as e:
            self.logger.error(e, exc_info=True)
            sys.exit()
