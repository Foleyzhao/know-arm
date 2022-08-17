# -*- coding: utf-8 -*-

import logging
import time

from utils.ip_utils import is_ipv4, is_ipv6
from core import Context
from core.enums import GatherProto, ShellReplyCode

from moudle.cmd import AsyncSSH, TelnetConn, AsyncWinRM

logger = logging.getLogger(__name__)


class Task:
    __slots__ = ('id', 'encoding', 'reply_to', 'connect_info', 'account', 'exec_cls', 'msg', 'body')

    def __init__(self, body, message):
        self.id = None
        self.encoding = 'utf-8'
        self.reply_to = None
        self.msg = message
        self.body: dict = body
        self.account = {}
        self.exec_cls = None
        self.connect_info = None

    def __getitem__(self, item):
        return self.body.get(item)

    def __setitem__(self, key, value):
        self.body['key'] = value

    def get(self, name):
        return self.body.get(name)

    def check(self):
        try:
            assert self.body, 'Task body is empty'
            if 'id' in self.body:
                self.id = self['id']
            else:
                self['id'] = self.id
            logger.info('Start parsing task id : {}'.format(self.id))
            assert ('reply_to' in self.msg.properties), 'Task without reply_to'
            self.reply_to = self.msg.properties["reply_to"]
            assert isinstance(self['account'], dict), 'Not account info'
            self.account = Account(
                username=self['account'].get('username'),
                password=self['account'].get('password')
            )
            assert isinstance(self['conn'], dict), 'Not connection info'
            self.connect_info = Connection(
                ip=self['conn'].get('ip'),
                port=self['conn'].get('port'),
                sys_type=self['conn'].get('sysType'),
                proto=self['conn'].get('proto'),
                encoding=self['conn'].get('encoding'),
                account=self.account
            )
            self.exec_cls = self.chose_cls(self.connect_info.proto)(connect_info=self.connect_info, reply_to=self.reply_to,
                                                                    body=self.body)
            return True
        except Exception as e:
            logger.warning(e, exc_info=True)
            if self.reply_to:
                res = {'id': self.id, 'cmd': '', 'encoding': self.encoding or '', 'stdout': '', 'stderr': '',
                       'returncode': None, 'code': ShellReplyCode.AUTHENTICATED_FAILED, 'err_info': str(e),
                       'start_time': time.time(), 'end_time': time.time()}
                exchange = str(self.reply_to).split('/')[0]
                routing_key = str(self.reply_to).split('/')[1]
                try:
                    Context.CTX.mq.send_as_task(res, exchange=exchange, routing_key=routing_key)
                except Exception as e:
                    logger.error('Failed to sent task {} result, reason {}'.format(self.id, e), exc_info=True)
            return False

    def run(self):
        self.exec_cls.run()

    @staticmethod
    def chose_cls(proto):
        if proto == GatherProto.SSH:
            return AsyncSSH
        elif proto == GatherProto.TELNET:
            return TelnetConn
        elif proto == GatherProto.WINRM:
            return AsyncWinRM
        raise ValueError('No support protocol %s' % proto)


class Connection:
    __slots__ = ('ip', 'port', 'sys_type', 'proto', 'encoding', 'account')

    def __init__(self, ip=None, port=None, sys_type=None, proto=None, encoding='utf-8', account=None):
        self.ip = ip
        self.port = port
        self.sys_type = sys_type
        self.proto = proto
        self.account = account
        self.encoding = encoding
        self.check()

    def check(self):
        assert self.proto, "Not protocol"
        assert self.ip, "Not ip"
        assert self.port, "Not port"

        if not is_ipv4(self.ip):
            if self.ip == 'localhost':
                self.ip = "127.0.0.1"
            elif is_ipv6(self.ip):
                raise ValueError('Not support ipv6 yet')
            else:
                raise ValueError('Invalid ip')

        if not isinstance(self.port, int):
            try:
                self.port = int(self.port)
            except Exception:
                raise ValueError("Invalid port")

        if self.port <= 0 or self.port > 65535:
            raise ValueError("Invalid port")

    def __str__(self):
        return "ip:%s port:%s proto:%s" % (self.ip, self.port, self.proto)


class Account(object):
    __slots__ = ('username', 'password',)

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.check()

    def check(self):
        assert self.username, 'Not username'
        assert self.password, 'Not password'

    def __str__(self):
        return "u:%s p:******" % self.username
