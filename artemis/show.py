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

__author__ = 'frostbane'
__date__ = '2016/03/04'


class ArtemisShow:
    commands = [
        ('a', 'all', None, 'List all comments.'),
        ('s', 'skip', '>', 'Skip lines starting with a substring.'),
        ('x', 'extract', [], 'Extract attachment(s) (provide '
                             'attachment number as argument). If the '
                             '"message" option is not specified the '
                             'attachment of the first message (the '
                             'issue itself) will be extracted. File '
                             'will be overwritten if it is already '
                             'existing. '
                             '(e.g. -x 1 -x 2 -m 1 -o tmp)'),
        ('i', 'index', 0, 'Message number to be shown (0 based '
                          'index, 0 is the issue and 1 onwards will '
                          'be the rest of the replies). If "extract" '
                          'option is set then the attachment of the '
                          'message will be extracted. This option is '
                          'ignored if the "all" option is specified.'),
        ('o', 'output', '"./tmp"', 'Extract output directory '
                                   '(e.g. -o "./files/attachments")'),
        ('', 'mutt', False, 'Use mutt to show the issue.')
    ]
    usage = 'hg ishow [OPTIONS] ID'

    def __init__(self):
        pass

    def show(self, ui, repo, id, **opts):
        """Shows issue ID, or possibly its comment COMMENT"""

        issue, id = Artemis.find_issue(ui, repo, id)
        if not issue:
            return ui.warn('No such issue\n')

        issues_dir = ui.config('artemis', 'issues',
                               default=Artemis.default_issues_dir)
        Artemis.create_missing_dirs(
                os.path.join(repo.root, issues_dir),
                issue)

        if opts.get('mutt'):
            return util.system('mutt -R -f %s' % issue)

        mbox = mailbox.Maildir(issue, factory=mailbox.MaildirMessage)

        # show the first mail
        ui.write('=' * 70 + '\n')
        keys = Artemis.order_keys_date(mbox)
        Artemis.write_message(ui, mbox[keys[0]], 0, skip=opts['skip'])

        if opts['all']:
            ui.write('=' * 70 + '\n')
            i = 0
            for k in keys:
                if (i > 0):
                    Artemis.write_message(ui, mbox[k], i,
                                          skip=opts['skip'])
                    ui.write('-' * 70 + '\n')
                i += 1
            return

        elif int(opts["index"]) > 0 and len(keys) > int(
                opts["index"]):
            # todo comments replied to this comment should also be shown
            reply_num = int(opts["index"])
            ui.write('-' * 70 + '\n')
            Artemis.write_message(
                    ui, mbox[keys[reply_num]], reply_num,
                    skip=opts['skip'])
            ui.write('=' * 70 + '\n')

        if opts['extract']:
            attachment_numbers = map(int, opts['extract'])
            msg = mbox[keys[opts["index"]]]

            counter = 1
            for part in msg.walk():
                ctype = part.get_content_type()
                maintype, subtype = ctype.split('/', 1)

                if maintype == 'multipart' or ctype == 'text/plain':
                    continue

                if counter in attachment_numbers:

                    filename = part.get_filename()
                    if not filename:
                        ext = mimetypes.guess_extension(
                                part.get_content_type()) or ''
                        filename = 'attachment-%03d%s' % (
                            counter, ext)

                    else:
                        filename = os.path.basename(filename)

                    dirname = opts["output"]
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)

                    pathFileName = os.path.join(dirname, filename)

                    fp = open(pathFileName, 'wb')
                    fp.write(part.get_payload(decode=True))
                    fp.close()

                counter += 1
