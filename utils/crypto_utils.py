# -*- coding: utf-8 -*-

import base64
import logging

logger = logging.getLogger(__name__)


def bytes2base64(b: bytes):
    return base64.b64encode(b)


def bytes_decode(b: bytes, default='utf-8') -> str:
    import cchardet
    try:
        res = b.decode(default)
    except Exception:
        detect = cchardet.detect(b)
        code = detect['encoding']
        res = b.decode(code)
    return res
