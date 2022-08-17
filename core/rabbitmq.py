# -*- coding: utf-8 -*-

import logging
from pprint import pformat
from threading import Thread

from amqp.exceptions import ConnectionForced
from kombu import Connection, Consumer, Exchange, Queue, eventloop
from kombu.pools import producers

from utils.dict_utils import find_attr
from utils.file_utils import read_yaml

logger = logging.getLogger(__name__)


def pretty(obj):
    return pformat(obj, indent=4)


class Broker:
    queue_attrs = ['queue_arguments', 'binding_arguments', 'consumer_arguments', 'durable', 'exclusive', 'auto_delete',
                   'no_ack', 'alias', 'bindings', 'no_declare', 'expires', 'message_ttl', 'max_length',
                   'max_length_bytes', 'max_priority']

    exchange_attrs = ['arguments', 'durable', 'passive', 'auto_delete', 'delivery_mode', 'no_declare']

    def __init__(self, broker_ip='localhost', port=5672, username=None, password=None, queue=None, routing_key=None,
                 exchange=None, exchange_type=None, **kwargs):
        self.exchanges = {}
        self.queues = {}
        self.host = broker_ip
        self.port = port
        self.username = username
        self.password = password
        self.vhost = kwargs['vhost'] if 'vhost' in kwargs else '%2F'
        self.kwargs = kwargs
        if queue and routing_key and exchange_type and exchange:
            _exchange_attr = find_attr(self.exchange_attrs, self.kwargs)
            _queue_attr = find_attr(self.queue_attrs, self.kwargs)
            self.add_conn(queue, routing_key, exchange_type, exchange, _queue_attr, _exchange_attr)

        self._conn = None

    def load(self, config_dict=None, config_path=None, enforce=True):
        config = {}
        if config_path:
            try:
                config.update(read_yaml(config_path, 'MQ_CONFIG'))
            except Exception as e:
                logger.error(e, exc_info=True)
                return
        elif config_dict:
            config.update(config_dict)
        else:
            return

        exchanges = config.pop('exchange') if 'exchange' in config else {}
        queues = config.pop('queue') if 'queue' in config else {}

        if enforce:
            self.__dict__.update(config)
        else:
            self.__dict__.update((k, v) for k, v in config.items() if (k not in self.__dict__) or v)

        for exchange in exchanges:
            self.add_exchange(**exchange)
        for queue in queues:
            self.add_queue(**queue)

    def _check(self):
        if not self.host:
            raise ValueError("Broker: invalid ip.")

        if not self.username:
            raise ValueError("Broker: invalid user.")

        if not self.password:
            raise ValueError("Broker: invalid passwd.")

    @property
    def amqp(self):
        if self.host and self.username and self.password:
            return 'amqp://{}:{}@{}:{}/{}'.format(self.username, self.password, self.host, self.port, self.vhost)
        else:
            logger.error("Missing rabbitmq parameter")
            raise

    def connection(self):
        if not self._conn:
            self._check()
            self._conn = Connection(self.amqp, **self.kwargs)
        return self._conn

    def add_exchange(self, **kwarg):
        _name = kwarg['name']
        _exchange = Exchange(**kwarg)
        self.exchanges[_name] = _exchange

    def add_queue(self, **kwarg):
        _name = kwarg['name']
        if kwarg['exchange'] in self.exchanges:
            kwarg['exchange'] = self.exchanges[kwarg['exchange']]
            _queue = Queue(**kwarg)
            self.queues[_name] = _queue
        else:
            logger.error('Not exist {} this exchange'.format(kwarg['exchange']))

    def add_conn(self, queue, routing_key, exchange_type, exchange, queue_attrs=None, exchange_attrs=None):
        if exchange_attrs is None:
            exchange_attrs = {}
        if queue_attrs is None:
            queue_attrs = {}
        self.add_exchange(name=exchange, type=exchange_type, **exchange_attrs)
        self.add_queue(name=queue, exchange=exchange, routing_key=routing_key, **queue_attrs)


class RabbitMQ:
    def __init__(self, broker, cb=None):
        self.broker = broker
        self.cb = cb if cb else self.handle_message
        self.is_running = False
        self.thread = None

    def run(self, queues=None, thread=True, **kwargs):
        res = []

        if not queues:
            res = [self.broker.queues[x] for x in self.broker.queues]
        else:
            if isinstance(queues, str):
                if queues in self.broker.queues:
                    res = [self.broker.queues[queues]]
                queues = [queues]
            for queue in set(queues):
                if queue not in self.broker.queues:
                    logger.error('Not queue named {}'.format(queue))
                else:
                    res.append(self.broker.queues[queue])

        if res:
            if thread:
                self.thread = Thread(target=self._run_consumer, args=(res,), kwargs=kwargs)
                self.thread.start()
            else:
                self._run_consumer(res, **kwargs)
        else:
            logger.warning('Not queue available, please check again!')
            return None

    @staticmethod
    def handle_message(body, message):
        logger.info(f'Received message: {body!r}')
        logger.info(f' properties:\n{pretty(message.properties)}')
        logger.info(f' delivery_info:\n{pretty(message.delivery_info)}')
        message.ack()

    def _run_consumer(self, queues, **kwargs):
        timeout = kwargs.get('timeout') or 1
        ignore_timeouts = kwargs.get('ignore_timeouts') or True
        with self.broker.connection() as connection:
            with Consumer(connection, queues, callbacks=[self.cb], **kwargs):
                self.is_running = True
                logger.debug("Rabbitmq is running at {}".format(self.broker.amqp))
                while self.is_running:
                    try:
                        for _ in eventloop(connection, timeout=timeout, ignore_timeouts=ignore_timeouts):
                            pass
                    except ConnectionForced as e:
                        self.is_running = False
                        logger.info('MQ received a force close commend: {}'.format(e))
                        break
                    except ConnectionResetError:
                        pass
                    except Exception as e:
                        self.is_running = False
                        logger.error('Cb has some problem {}'.format(e), exc_info=True)
                        break

    def send_as_task(self, data, block=False, **kwargs):
        with producers[self.broker.connection()].acquire(block=block) as producer:
            producer.publish(data, **kwargs)
