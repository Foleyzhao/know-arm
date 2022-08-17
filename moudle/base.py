# -*- coding: utf-8 -*-

import json
import logging
import time

from core import Context
from utils.json_utils import MsgEncoder

logger = logging.getLogger(__name__)


class Base:

    def __init__(self, task):
        self.task = task
        self.data = None

    def run(self):
        logger.info('Task {} start!'.format(self.task.id))
        self.task.result.start_time = time.time()

    def handle(self):
        self.task.result.end_time = time.time()

    def reply(self):
        if self.task.reply:
            try:
                Context.CTX.mq.send_as_task(json.dumps(self.task.result.__dict__), exchange=self.task.exchange,
                                            routing_key=self.task.routing_key)
            except Exception as e:
                logger.error('Failed to sent task {} result, reason {}'.format(self.task.id, e), exc_info=True)
        logger.info('Task {} end!'.format(self.task.id))
