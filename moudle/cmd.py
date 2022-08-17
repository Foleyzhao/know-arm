# -*- coding: utf-8 -*-

import asyncio
import logging
import re
import time

import asyncssh
import httpx._exceptions as exceptions
import telnetlib3
from asyncssh import PermissionDenied, ConnectionLost
from asyncwinrm import Session

from utils.crypto_utils import bytes2base64, bytes_decode
from core.context import Context
from core.enums import ShellReplyCode as ReCode, ShellReplyMessage as ReMes

logger = logging.getLogger(__name__)


class CmdBase:
    __slots__ = ('connect_info', 'cmd', 'reply_to', 'res', 'id', 'task', 'timeout', 'encoding', 'is_replied')

    def __init__(self, connect_info=None, reply_to=None, body=None):
        self.id = body.get('id')
        self.task = body.get('task')
        assert self.task, 'task data is empty'
        self.cmd = self.task.get('cmd')
        assert self.cmd, 'not exist cmd'
        self.timeout = self.task.get('mto') or 100
        self.encoding = body.get('encoding') or False
        self.connect_info = connect_info
        self.reply_to = reply_to
        self.res = {'id': self.id, 'cmd': str(self.cmd), 'encoding': self.encoding or '', 'stdout': '',
                    'stderr': '', 'returncode': None, 'code': ReCode.SUCCESS, 'err_info': ''}
        self.is_replied = False

    def run(self):
        raise NotImplementedError(f'{self.__class__.__name__}.parse callback is not defined')

    def reply(self):
        if not self.is_replied:
            self.res['end_time'] = time.time()
            exchange = str(self.reply_to).split('/')[0]
            routing_key = str(self.reply_to).split('/')[1]
            try:
                self.log()
                Context.CTX.mq.send_as_task(self.res, exchange=exchange, routing_key=routing_key)
                self.is_replied = True
            except Exception as e:
                logger.error('Failed to sent task {} result, reason {}'.format(self.id, e), exc_info=True)

    def log(self):
        if self.res['code'] >= 0:
            logger.info('Task {} Success!'.format(self.id))
            logger.debug('Result: {}'.format(self.res))
        else:
            logger.info('Task {} Failed!'.format(self.id))
            logger.debug('Result: {}'.format(self.res))


class AsyncSSH(CmdBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task = None
        self.conn_cnt = 0

    def run(self):
        self.res['start_time'] = time.time()
        self.task = Context.CTX.coro.add_task(self.async_task())

    async def async_task(self):
        try:
            async with asyncssh.connect(
                    host=self.connect_info.ip,
                    port=self.connect_info.port,
                    username=self.connect_info.account.username,
                    password=self.connect_info.account.password,
                    known_hosts=None) as conn:
                if self.cmd:
                    self.parse_output(await conn.run(self.cmd, timeout=self.timeout))
                await conn.run('exit', timeout=self.timeout)
        except asyncio.exceptions.CancelledError:
            self.res['code'] = ReCode.MANUAL_CANCELLED
            self.res['err_info'] = ReMes.MANUAL_CANCELLED
        except PermissionDenied:
            self.res['code'] = ReCode.PERMISSION_DENIED
            self.res['err_info'] = ReMes.PERMISSION_DENIED
        except asyncssh.process.TimeoutError:
            self.res['code'] = ReCode.HIT_EOF_TIME_OUT
            self.res['err_info'] = ReMes.HIT_EOF_TIME_OUT
        except TimeoutError:
            self.res['code'] = ReCode.CONNECTION_TIME_OUT
            self.res['err_info'] = ReMes.CONNECTION_TIME_OUT
        except (ConnectionResetError, ConnectionLost):
            if not await self.re_connecting():  # [Connect reset by peer] or [Connection lost]
                self.res['code'] = ReCode.CONNECTION_TIME_OUT
                self.res['err_info'] = ReMes.CONNECTION_TIME_OUT
        except UnicodeDecodeError as e:
            self.res['code'] = ReCode.ERROR_DECODING
            self.res['err_info'] = str(e)
        except Exception as e:
            logger.error(e, exc_info=True)
            self.res['code'] = ReCode.UNKNOWN_ERROR
            self.res['err_info'] = str(e)
        finally:
            self.reply()

    async def re_connecting(self, cnt=3):
        while self.conn_cnt <= cnt:
            if not self.is_replied:
                await asyncio.sleep(2)
                self.conn_cnt += 1
                await self.async_task()
            else:
                break
        return True if self.conn_cnt <= cnt else False

    def parse_output(self, out):
        self.res['stdout'] = out.stdout
        self.res['stderr'] = out.stderr
        self.res['returncode'] = out.returncode
        if out.returncode < 0:
            self.res['code'] = ReCode.UNKNOWN_ERROR
            self.res['err_info'] = ReMes.UNKNOWN_ERROR


class AsyncWinRM(CmdBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task = None

    def run(self):
        self.res['start_time'] = time.time()
        self.task = Context.CTX.coro.add_task(self.async_task())

    @property
    def target(self):
        if self.connect_info.port:
            return "{}:{}".format(self.connect_info.ip, self.connect_info.port)
        else:
            return self.connect_info.ip

    async def async_task(self):
        try:
            s = Session(self.target, auth=(self.connect_info.account.username, self.connect_info.account.password))
            if self.cmd:
                response = await s.run_cmd(self.cmd, ['/all'])
                self.parse_output(response)
            else:
                await s.run_cmd('echo test', ['/all'])
        except asyncio.exceptions.CancelledError:
            self.res['code'] = ReCode.MANUAL_CANCELLED
        except exceptions.HTTPStatusError as e:
            if '401 Client Error' in str(e):
                self.res['code'] = ReCode.PERMISSION_DENIED
            else:
                logger.error(e, exc_info=True)
                self.res['code'] = ReCode.UNKNOWN_ERROR
                self.res['err_info'] = str(e)
        except asyncssh.process.TimeoutError:
            self.res['code'] = ReCode.HIT_EOF_TIME_OUT
        except UnicodeDecodeError as e:
            self.res['code'] = ReCode.ERROR_DECODING
            self.res['err_info'] = str(e)
        except Exception as e:
            if 'Connection lost' in str(e):
                self.res['code'] = ReCode.CONNECTION_TIME_OUT
            else:
                logger.error(e, exc_info=True)
                self.res['code'] = ReCode.UNKNOWN_ERROR
                self.res['err_info'] = str(e)
        finally:
            self.reply()

    def parse_output(self, out):
        self.res['stdout'] = bytes_decode(out.std_out, self.encoding) if self.encoding else bytes2base64(out.std_out)
        self.res['stderr'] = bytes_decode(out.std_err, self.encoding) if self.encoding else bytes2base64(out.std_err)
        self.res['returncode'] = out.status_code
        if out.status_code < 0:
            self.res['code'] = ReCode.UNKNOWN_ERROR
            self.res['err_info'] = ReMes.UNKNOWN_ERROR


class TelnetConn(CmdBase):
    user_ps = b'login:'
    pass_ps = b'Password:'
    success_match = '(?i)(Last login:|Last failed login:)'
    success_match_byte = b'(?i)(Last login:|Last failed login:)'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task = None
        self.writer = None
        self.reader = None
        self._start_text = None
        self._is_connected = False
        self._is_closed = False

    def run(self):
        self.res['start_time'] = time.time()
        self.task = Context.CTX.coro.add_task(self.async_task())

    async def async_task(self):
        try:
            await self.connect()
            if self.cmd:
                self.parse_output(await self.parse_cmd(self.cmd))
        except OSError:
            self.res['code'] = ReCode.CONNECTION_TIME_OUT
            self.res['err_info'] = ReMes.CONNECTION_TIME_OUT
        except LoginError:
            self.res['code'] = ReCode.PERMISSION_DENIED
            self.res['err_info'] = ReMes.PERMISSION_DENIED
        except UnicodeDecodeError as e:
            self.res['code'] = ReCode.ERROR_DECODING
            self.res['err_info'] = str(e)
        except Exception as e:
            logger.error(e, exc_info=True)
            self.res['code'] = ReCode.UNKNOWN_ERROR
            self.res['err_info'] = str(e)
        finally:
            self.reply()
            await self.close()

    async def close(self):
        try:
            if self._is_connected:
                if not self._is_closed:
                    self.writer.close()
                    self._is_closed = True
        except Exception:
            pass

    def parse_output(self, out):
        if out.endswith(self._start_text):
            out = out[:-len(self._start_text)]
        self.res['stdout'] = out if self.encoding else bytes2base64(out)
        self.res['code'] = ReCode.SUCCESS

    async def connect(self):
        self.reader, self.writer = await telnetlib3.open_connection(
            self.connect_info.ip, self.connect_info.port, encoding=self.encoding or 'utf8', connect_maxwait=5.0)
        _ = await self.reader.readuntil(TelnetConn.user_ps)
        await self.write(self.connect_info.account.username)
        _ = await self.reader.readuntil(TelnetConn.pass_ps)
        await self.write(self.connect_info.account.password)
        login_res = await self.read_all()
        if re.search(TelnetConn.success_match if self.encoding else TelnetConn.success_match_byte, login_res):
            self._start_text = login_res.split('\r\n' if self.encoding else b'\r\n')[-1]
            self._is_connected = True
        else:
            raise LoginError

    async def write(self, data):
        data = data + '\n' if self.encoding else data.encode() + b'\n'
        self.writer.write(data)
        await self.writer.drain()

    async def parse_cmd(self, cmd):
        await self.write(cmd)
        res = await self.read_all()
        # TODO temp
        # if ('E437') in res:
        #     res = await self.parse_cmd('')
        return res

    async def read_all(self):
        # TODO should we set timeout or others?
        res = '' if self.encoding else b''
        while True:
            bl = len(self.reader._buffer)
            res += await self.reader.read(bl)
            await asyncio.sleep(2)
            if not self.reader._buffer:
                break
        return res


class LoginError(Exception):
    pass
