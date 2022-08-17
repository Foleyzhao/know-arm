# -*- coding: utf-8 -*-

import json
from datetime import datetime, date
from uuid import UUID

import numpy as np


class MsgEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, type(np.ndarray)):
            return obj.tolist()
        elif isinstance(obj, UUID):
            return obj.hex
        else:
            return json.JSONEncoder.default(self, obj)
