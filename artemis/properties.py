#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'frostbane'
__date__ = '2016/03/03'

class ArtemisProperties(dict):
    def __init__(self, msg):
        # Borrowed from termcolor
        for k, v in zip(['bold', 'dark', '', 'underline', 'blink', '',
                         'reverse', 'concealed'], range(1, 9)) + \
                zip(['grey', 'red', 'green', 'yellow', 'blue',
                     'magenta', 'cyan', 'white'], range(30, 38)):
            self[k] = '\033[' + str(v) + 'm'
        self['reset'] = '\033[0m'
        del self['']

        for k, v in msg.items():
            self[k] = v

    def __contains__(self, k):
        return super(ArtemisProperties, self).__contains__(
            k.lower())

    def __getitem__(self, k):
        if k not in self:
            return ''
        return super(ArtemisProperties, self).__getitem__(
            k.lower())

    def __setitem__(self, k, v):
        super(ArtemisProperties, self).__setitem__(k.lower(), v)
