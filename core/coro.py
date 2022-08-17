# -*- coding: utf-8 -*-

import sys
import time
import asyncio
import logging
from threading import Thread

logger = logging.getLogger(__name__)


# TODO 需要增加异常输出  Coroutine

class Coro(Thread):
    def __init__(self, name='coroutine', sem=40, daemon=False):
        super().__init__(name=name, daemon=daemon)
        self.loop = asyncio.new_event_loop()
        self.tasks = {}
        # self.loop.set_exception_handler(self.custom_exception_handler)
        self._sem_count = sem
        self.sem = None

    def __getitem__(self, item):
        try:
            return self.tasks[item]
        except KeyError:
            print('Task {} does not exist'.format(item))
            raise

    def __repr__(self):
        d = {}
        for name in self.tasks:
            d[name] = {'state': self[name]._state}
        return str(d)

    def run(self) -> None:
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

    async def sem_task(self, coro):
        # 对task增加信号量，限制同一时间正在执行的任务数
        if not self.sem:
            self.sem = asyncio.Semaphore(self._sem_count)
        async with self.sem:
            return await coro

    def add_task(self, coro, name=None, sem=False):
        if name in self.tasks:
            return False
        if sem:
            task = self.loop.create_task(self.sem_task(coro))
        else:
            task = self.loop.create_task(coro, name=name)
        self.loop._csock.send(b'\0')
        name = task.get_name()
        self.tasks[name] = task
        return name

    def status(self, name):
        return self[name]._state

    def stop_task(self, name, nowait=False):
        self[name].cancel()
        if not nowait:
            while not self.tasks[name].cancelled():
                time.sleep(0.5)

    def get_result(self, name):
        try:
            res = self[name].result()
            del self.tasks[name]
        except asyncio.exceptions.CancelledError:
            print('Task {} cancelled'.format(name))
            res = 'Task canceled'
        except Exception as e:
            res = str(e)
        return res

    def is_done(self, name):
        return self[name].done()
