# -*- coding: utf-8 -*-

from core.enums import TaskType
from moudle.info import GetEngineInfo


class Task:
    __slots__ = ('id', 'type', 'args', 'extra', 'exec_cls', 'reply', 'exchange', 'routing_key', 'result')

    def __init__(self, body, message):
        self.id = body['id'] if 'id' in body else None
        self.type = body['type'] if 'id' in body else None
        self.args = body['args'] if 'id' in body else None
        self.extra = body['extra'] if 'id' in body else None
        self.exec_cls = None
        self.reply = "reply_to" in message.properties
        self.exchange = message.properties["reply_to"].split('/')[0] if self.reply else None
        self.routing_key = message.properties["reply_to"].split('/')[1] if self.reply else None
        self.result = Result(taskId=self.id, taskType=self.type)
        self.check()

    def check(self):
        assert self.id, "Not id"
        assert self.type, "Not type"

    def exec(self):
        self.exec_cls.run()
        self.exec_cls.handle()
        self.exec_cls.reply()

    def __str__(self):
        return "Task[id:%s type:%s]" % (self.id, self.type)


class InfoTask(Task):
    def __init__(self, body, message):
        super().__init__(body, message)
        self.exec_cls = GetEngineInfo(task=self)
        self.check()

    def check(self):
        super().check()
        assert self.type == TaskType.INFO, "Task type mismatch"


class Result:
    __slots__ = ('id', 'type', 'result', 'extra', 'start_time', 'end_time')

    def __init__(self, taskId=None, taskType=None, result=None, extra=None):
        self.id = taskId
        self.type = taskType
        self.result = result
        self.extra = extra
        self.start_time = None
        self.end_time = None
        self.check()

    def check(self):
        assert self.id, "Not id"
        assert self.type, "Not type"

    def __str__(self):
        return "Result[id:%s type:%s]" % (self.id, self.type)
