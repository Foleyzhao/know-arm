# -*- coding: utf-8 -*-

import socket

from core import Context
from moudle.base import Base


class GetEngineInfo(Base):

    def __init__(self, task):
        super().__init__(task)

    def run(self):
        super().run()
        hostname = socket.gethostname()
        self.data = {'hostname': hostname, 'ip': socket.gethostbyname(hostname), 'version': Context.CTX.version}

    def handle(self):
        super().handle()
        self.task.result.result = self.data
