# -*- coding: utf-8 -*-

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from moudle.gather import Task
from .enums import TaskType
from .constant import MAX_WORKER
from .model import InfoTask

logger = logging.getLogger(__name__)


class Dispatcher:
    executor = ThreadPoolExecutor(max_workers=MAX_WORKER)

    @classmethod
    def submit(cls, fn, *args, **kwargs):
        cls.executor.submit(fn, *args, **kwargs)

    @classmethod
    def handle_msg(cls, body, message):
        cls.submit(cls._handle_msg_in_thread, body, message)

    @classmethod
    def _handle_msg_in_thread(cls, body, message):
        body = cls.decode_body(body)

        logger.debug('Receiving task: {}'.format(body))
        logger.debug("Msg hdr:%s", message.headers)
        logger.debug("Msg pros:%s", message.properties)
        logger.debug("Msg delivery:%s", message.delivery_info)

        if body['type'] == TaskType.INFO:
            task = InfoTask(body, message)
            task.exec()
            pass
        elif body['type'] == TaskType.GATHER:
            task = Task(body, message)
            if task.check():
                task.run()
            else:
                logger.warning('Check failed with message {}'.format(body))
                pass
        elif body['type'] == TaskType.UNKNOWN:
            logger.warning("Unknown type")
            pass
        else:
            logger.warning("This type is not supported: %s", body['type'])
            pass

    @staticmethod
    def decode_body(body):
        try:
            if not isinstance(body, dict):
                body = json.loads(body)
            if 'type' not in body:
                body['type'] = 'UNKNOWN'
        except Exception as e:
            logger.error(e, exc_info=True)
            body = {'type': ''}

        return body

    @classmethod
    def stop_task(cls, task_id):
        pass
