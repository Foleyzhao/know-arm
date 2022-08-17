# -*- coding: utf-8 -*-

import asyncio
import logging
import sys
from multiprocessing import Process

logger = logging.getLogger(__name__)


class Coroutine(Process):

    def __init__(self, ctx):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.tasks = {}
        self.queue = ctx.queue

    def __getitem__(self, item):
        try:
            return self.tasks[item]
        except KeyError:
            logger.warning('Task {} does not exist'.format(item))
            raise

    def run(self):
        logger.info('Coroutine process start')
        try:
            asyncio.set_event_loop(self.loop)
        except Exception:
            logger.error('Coroutine start failed')
            sys.exit()
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()
            logger.info('Coroutine process end')

    def add_task(self, coroutine, name=None):
        if name in self.tasks:
            logger.warning("Task %s already exists" % name)
            return
        task = self.loop.create_task(coroutine, name=name)
        name = task.get_name()
        self.tasks[name] = task
        return name
