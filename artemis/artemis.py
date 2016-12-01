#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Dmitriy Morozov <hg@foxcub.org>, 2007 -- 2009
__author__ = "Dmitriy Morozov"

"""A very simple and lightweight issue tracker for Mercurial."""

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
from properties import ArtemisProperties


def singleton(cls):
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()

        return instances[cls]

    return getinstance


# @singleton
class Artemis:
    """Artemis static and common functions
    """
    state = {
        'new'     : ['new'],
        'resolved': [
            'fixed',
            'resolved'
        ]
    }
    default_state = 'new'
    default_issues_dir = ".issues"
    filter_prefix = ".filter"
    date_format = '%a, %d %b %Y %H:%M:%S %1%2'
    maildir_dirs = ['new', 'cur', 'tmp']
    default_format = '%(id)s (%(len)3d) [%(state)s]: %(Subject)s'

    # def __init__(self):
    #     pass

    @staticmethod
    def create_all_missing_dirs(issues_path, issues):
        for issue in issues:
            Artemis.create_missing_dirs(issues_path, issue)

    @staticmethod
    def find_issue(ui, repo, id):
        issues_dir = ui.config('artemis', 'issues',
                               default=Artemis.default_issues_dir)
        issues_path = os.path.join(repo.root, issues_dir)
        if not os.path.exists(issues_path):
            return False

        issues = glob.glob(os.path.join(issues_path, id + '*'))

        if len(issues) == 0:
            return False, 0

        elif len(issues) > 1:
            ui.status("Multiple choices:\n")
            for issue in issues:
                ui.status('  ', Artemis.get_issue_id(ui, repo, issue), '\n')

            return False, 0

        else:
            return issues[0], Artemis.get_issue_id(ui, repo, issues[0])

    @staticmethod
    def get_issues_dir(ui):
        issues_dir = ui.config('artemis',
                               'issues',
                               default=Artemis.default_issues_dir)

        return issues_dir

    @staticmethod
    def get_issues_path(ui, repo):
        """gets the full path of the issues directory. returns nothing
        if the path does not exist.

        :Example:
            issues_path = Artemis.get_issues_path(ui, repo)
            if not issues_path:
                # error
            else
                # path exists

        """
        issues_dir = Artemis.get_issues_dir(ui)
        issues_path = os.path.join(repo.root, issues_dir)

        if not os.path.exists(issues_path):
            return

        return issues_path

    @staticmethod
    def get_all_issues(ui, repo):
        # Find issues
        issues_path = Artemis.get_issues_path(ui, repo)
        if not issues_path:
            return []

        issues = glob.glob(os.path.join(issues_path, '*'))

        Artemis.create_all_missing_dirs(issues_path, issues)

        return issues

    @staticmethod
    def get_all_mboxes(ui, repo):
        """gets a list of all available mboxes with an added extra
        property "issue"

        :param ui: mercurial ui object
        :param repo: mercurial repo object
        :return: list of all available mboxes
        """
        issues = Artemis.get_all_issues(ui, repo)
        if not issues:
            return []

        mboxes = []
        for issue in issues:
            mbox = mailbox.Maildir(issue,
                                   factory=mailbox.MaildirMessage)

            root = Artemis.find_root_key(mbox)
            if not root:  # root is None
                continue

            # add extra property
            mbox.issue = issue
            mboxes.append(mbox)

        return mboxes


    @staticmethod
    def get_properties(property_list):
        return [p.split('=') for p in property_list]

    @staticmethod
    def write_message(ui, message, index=0, skip=None):
        if index:
            ui.write("Comment: %d\n" % index)

        if ui.verbose:
            Artemis.show_text(ui, message.as_string().strip(), skip)
            return

        if 'From' in message:
            ui.write('From: %s\n' % message['From'])
        if 'Date' in message:
            ui.write('Date: %s\n' % message['Date'])
        if 'Subject' in message:
            ui.write('Subject: %s\n' % message['Subject'])
        if 'State' in message:
            ui.write('State: %s\n' % message['State'])

        counter = 1
        for part in message.walk():
            ctype = part.get_content_type()
            maintype, subtype = ctype.split('/', 1)

            if maintype == 'multipart':
                continue

            if ctype == 'text/plain':
                ui.write('\n')
                Artemis.show_text(ui, part.get_payload().strip(),
                                  skip)

            else:
                filename = part.get_filename()
                ui.write('\n' + '%d: Attachment [%s, %s]: %s' % (
                    counter, ctype,
                    Artemis.humanreadable(len(part.get_payload())),
                    filename) + '\n')
                counter += 1

    @staticmethod
    def show_text(ui, text, skip=None):
        for line in text.splitlines():
            if not skip or not line.startswith(skip):
                ui.write(line + '\n')
        ui.write('\n')

    @staticmethod
    def show_mbox(ui, mbox, comment, **opts):
        # Output the issue (or comment)
        if comment >= len(mbox):
            comment = 0
            ui.warn(
                'Comment out of range, showing the issue itself\n')

        keys = Artemis.order_keys_date(mbox)
        root = keys[0]
        msg = mbox[keys[comment]]
        ui.write('=' * 70 + '\n')

        if comment:
            ui.write('Subject: %s\n' % mbox[root]['Subject'])
            ui.write('State: %s\n' % mbox[root]['State'])
            ui.write('-' * 70 + '\n')

        Artemis.write_message(ui, msg, comment,
                              skip=('skip' in opts) and opts['skip'])
        ui.write('-' * 70 + '\n')

        # Read the mailbox into the messages and children dictionaries
        messages = {}
        children = {}
        i = 0
        for k in keys:
            m = mbox[k]
            messages[m['Message-Id']] = (i, m)
            children.setdefault(m['In-Reply-To'], []).append(
                m['Message-Id'])
            i += 1

        # Safeguard against infinte loop on empty Message-Id
        children[
            None] = []

        # Iterate over children
        id = msg['Message-Id']
        id_stack = (id in children and
                    map(lambda x: (x, 1),
                        reversed(children[id]))) or []
        if not id_stack:
            return

        ui.write('Comments:\n')
        while id_stack:
            id, offset = id_stack.pop()
            id_stack += (id in children and
                         map(lambda x: (x, offset + 1),
                             reversed(children[id]))
                         ) or []

            index, msg = messages[id]
            ui.write('  ' * offset +
                     '%d: [%s] %s\n' %
                     (index,
                      util.shortuser(msg['From']), msg['Subject']))

        ui.write('-' * 70 + '\n')

    @staticmethod
    def find_root_key(maildir):
        for k, m in maildir.iteritems():
            if 'in-reply-to' not in m:
                return k

    @staticmethod
    def order_keys_date(mbox):
        keys = mbox.keys()
        root = Artemis.find_root_key(mbox)
        keys.sort(lambda k1, k2: -(k1 == root) or
                                 cmp(util.parsedate(mbox[k1]['date']),
                                     util.parsedate(
                                         mbox[k2]['date'])))

        return keys

    @staticmethod
    def create_missing_dirs(issues_path, issue):
        for dir in Artemis.maildir_dirs:
            path = os.path.join(issues_path, issue, dir)
            if not os.path.exists(path):
                os.mkdir(path)

    @staticmethod
    def humanreadable(size):
        if size > 1024 * 1024:
            return '%5.1fM' % (float(size) / (1024 * 1024))

        elif size > 1024:
            return '%5.1fK' % (float(size) / 1024)

        else:
            return '%dB' % size

    @staticmethod
    def get_issue_id(ui, repo, issue):
        """get the issue id provided the issue"""
        # Find issues
        issues_dir = ui.config('artemis', 'issues',
                               default=Artemis.default_issues_dir)
        issues_path = os.path.join(repo.root, issues_dir)
        if not os.path.exists(issues_path):
            return ""

        # +1 for trailing /
        return issue[len(issues_path) + 1:]


# vim: expandtab
