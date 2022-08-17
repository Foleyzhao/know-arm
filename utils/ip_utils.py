# -*- coding: utf-8 -*-

import logging

from IPy import IP

logger = logging.getLogger(__name__)


def is_ip(target):
    try:
        res = IP(target)
        return res if res and res.len() == 1 else False
    except ValueError:
        return False


def is_ipv6(target):
    try:
        tmp = is_ip(target)
        return tmp and tmp.version() == 6
    except Exception:
        return False


def is_ipv4(target):
    try:
        tmp = is_ip(target)
        return tmp and tmp.version() == 4
    except Exception:
        return False
