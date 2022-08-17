# -*- coding: utf-8 -*-

class Env:
    DEV = "DEVELOPMENT"
    PROD = "PRODUCTION"


class TaskType:
    INFO = 'info'
    DETECT = 'detect'
    GATHER = 'gather'
    SCAN = 'scan'
    SITE = 'site'
    UNKNOWN = 'unknown'


class GatherProto:
    SSH = 'ssh'
    WINRM = 'winrm'
    TELNET = 'telnet'


class ShellReplyCode:
    SUCCESS = 0
    CONNECTION_TIME_OUT = -1
    PERMISSION_DENIED = -2
    MANUAL_CANCELLED = -3
    HIT_EOF_TIME_OUT = -4
    ERROR_DECODING = -5
    AUTHENTICATED_FAILED = -6
    UNKNOWN_ERROR = -999


class ShellReplyMessage:
    SUCCESS = 'success'
    CONNECTION_TIME_OUT = 'connection time out'
    PERMISSION_DENIED = 'permission denied'
    MANUAL_CANCELLED = 'manual cancelled'
    HIT_EOF_TIME_OUT = 'hit eof time out'
    ERROR_DECODING = 'error decoding'
    AUTHENTICATED_FAILED = 'authenticated failed'
    UNKNOWN_ERROR = 'unknown error'
