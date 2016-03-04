#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mercurial import hg, util, commands
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

__author__ = 'frostbane'
__date__ = '2016/03/02'


cmdtable = {
    'ilist'       : (ArtemisList().list,
                     ArtemisList.commands,
                     _(ArtemisList.usage)),
    'iadd'        : (ArtemisAdd().add,
                     ArtemisAdd.commands,
                     _(ArtemisAdd.usage)),
    'ishow'       : (ArtemisShow().show,
                     ArtemisShow.commands,
                     _(ArtemisShow.usage)),
}

if __name__ == "__main__":
    pass
