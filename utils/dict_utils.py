# -*- coding: utf-8 -*-

def find_attr(keys: list, target: dict):
    res = {}
    for key in target:
        if key in keys:
            res[key] = target[key]
    return res
