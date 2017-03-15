#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mercurial import hg, util, commands, cmdutil
from mercurial.i18n import _
import sys, os, time, random, mailbox, glob, socket, ConfigParser
import mimetypes
from email import encoders
from email.generator import Generator
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itertools import izip
from artemis import Artemis
from list import ArtemisList
from add import ArtemisAdd
from show import ArtemisShow
from find import ArtemisFind

__author__ = 'frostbane'
__date__ = '2016/03/02'


cmdtable = {}
command = cmdutil.command(cmdtable)

@command('ifind', ArtemisFind.commands, ArtemisFind.usage)
def find(ui, repo, id=None, **opts):
    '''find issues'''
    return ArtemisFind().find(ui, repo, id, **opts)

@command('ishow', ArtemisShow.commands, ArtemisShow.usage)
def show(ui, repo, id=None, **opts):
    '''show issue details'''
    return ArtemisShow().show(ui, repo, id, **opts)

@command('ilist', ArtemisList.commands, ArtemisList.usage)
def list(ui, repo, id=None, **opts):
    '''list issues'''
    return ArtemisList().list(ui, repo, **opts)

@command('iadd', ArtemisAdd.commands, ArtemisAdd.usage)
def add(ui, repo, id=None, **opts):
    '''add / edit issues'''
    return ArtemisAdd().add(ui, repo, id, **opts)

if __name__ == "__main__":
    pass
