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


class ArtemisAdd:
    commands = [
        ('a', 'attach', [], 'Attach file(s) '
                            '(e.g., -a filename1 -a filename2,'
                            '-a ~/Desktop/file.zip)'),
        ('p', 'property', [], 'Update properties '
                              '(e.g., -p state=fixed)'),
        ('n', 'no-property-comment', None, 'Do not add a comment '
                                           'about changed properties'),
        ('m', 'message', '', 'Use <text> as an issue subject'),
        ('i', 'index', '0', 'Index of the message to comment.'),
        ('c', 'commit', False, 'Perform a commit after the addition')
    ]
    usage = 'hg iadd [OPTIONS] [ID] [COMMENT]'

    def __init__(self):
        pass

    def attach_files(self, msg, filenames):
        outer = MIMEMultipart()
        for k in msg.keys():
            outer[k] = msg[k]

        outer.attach(MIMEText(msg.get_payload()))

        for filename in filenames:
            ctype, encoding = mimetypes.guess_type(filename)
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded
                # (compressed), so use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            if maintype == 'text':
                fp = open(filename)
                # Note: we should handle calculating the charset
                attachment = MIMEText(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'image':
                fp = open(filename, 'rb')
                attachment = MIMEImage(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'audio':
                fp = open(filename, 'rb')
                attachment = MIMEAudio(fp.read(), _subtype=subtype)
                fp.close()
            else:
                fp = open(filename, 'rb')
                attachment = MIMEBase(maintype, subtype)
                attachment.set_payload(fp.read())
                fp.close()
                # Encode the payload using Base64
                encoders.encode_base64(attachment)
            # Set the filename parameter
            attachment.add_header('Content-Disposition', 'attachment',
                                  filename=os.path.basename(filename))
            outer.attach(attachment)
        return outer

    def random_id(self):
        return "%x" % random.randint(2 ** 63, 2 ** 64 - 1)

    def add(self, ui, repo, id=None, **opts):
        """Adds a new issue, or comment to an existing issue ID or its
        comment COMMENT"""

        comment = int(opts["index"])

        # First, make sure issues have a directory
        issues_dir = ui.config('artemis', 'issues',
                               default=Artemis.default_issues_dir)
        issues_path = os.path.join(repo.root, issues_dir)
        if not os.path.exists(issues_path):
            os.mkdir(issues_path)

        if id:
            issue_fn, issue_id = Artemis.find_issue(ui, repo, id)
            if not issue_fn:
                ui.warn('No such issue\n')
                return
            Artemis.create_missing_dirs(issues_path, issue_id)
            mbox = mailbox.Maildir(issue_fn,
                                   factory=mailbox.MaildirMessage)
            keys = Artemis.order_keys_date(mbox)
            root = keys[0]

        user = ui.username()

        default_issue_text = "From: %s\nDate: %s\n" % (
            user, util.datestr(format=Artemis.date_format))
        if not id:
            default_issue_text += "State: %s\n" % Artemis.default_state
            default_issue_text += "Subject: brief description\n\n"
        else:
            subject = \
                mbox[(comment < len(mbox) and keys[comment]) or root][
                    'Subject']
            if not subject.startswith('Re: '):
                subject = 'Re: ' + subject
            default_issue_text += "Subject: %s\n\n" % subject
        default_issue_text += "Detailed description."

        # Get properties, and figure out if we need
        # an explicit comment
        properties = Artemis.get_properties(opts['property'])
        no_comment = id and properties and opts['no_property_comment']
        message = opts['message']

        # Create the text
        if message:
            if not id:
                state_str = 'State: %s\n' % Artemis.default_state
            else:
                state_str = ''
            issue = "From: %s\nDate: %s\nSubject: %s\n%s" % \
                    (user, util.datestr(format=Artemis.date_format),
                     message,
                     state_str)
        elif not no_comment:
            issue = ui.edit(default_issue_text, user)

            if issue.strip() == '':
                ui.warn('Empty issue, ignoring\n')
                return
            if issue.strip() == default_issue_text:
                ui.warn('Unchanged issue text, ignoring\n')
                return
        else:
            # Write down a comment about updated properties
            properties_subject = ', '.join(
                    ['%s=%s' % (property, value) for (property, value)
                     in
                     properties])

            issue = "From: %s\nDate: %s\nSubject: changed " \
                    "properties (%s)\n" % \
                    (user, util.datestr(format=Artemis.date_format),
                     properties_subject)

        # Create the message
        msg = mailbox.MaildirMessage(issue)
        if opts['attach']:
            outer = self.attach_files(msg, opts['attach'])

        else:
            outer = msg

        # Pick random filename
        if not id:
            issue_fn = issues_path
            while os.path.exists(issue_fn):
                issue_id = self.random_id()
                issue_fn = os.path.join(issues_path, issue_id)
            mbox = mailbox.Maildir(issue_fn,
                                   factory=mailbox.MaildirMessage)
            keys = Artemis.order_keys_date(mbox)
        # else: issue_fn already set

        # Add message to the mailbox
        mbox.lock()
        if id and comment >= len(mbox):
            ui.warn(
                    'No such comment number in mailbox, commenting on the '
                    'issue itself\n')

        if not id:
            outer.add_header('Message-Id', "<%s-0-artemis@%s>" % (
                issue_id, socket.gethostname()))

        else:
            root = keys[0]
            outer.add_header('Message-Id', "<%s-%s-artemis@%s>" % (
                issue_id, self.random_id(), socket.gethostname()))
            outer.add_header('References', mbox[
                (comment < len(mbox) and keys[comment]) or root][
                'Message-Id'])
            outer.add_header('In-Reply-To', mbox[
                (comment < len(mbox) and keys[comment]) or root][
                'Message-Id'])
        new_bug_path = issue_fn + '/new/' + mbox.add(outer)
        commands.add(ui, repo, new_bug_path)

        # Fix properties in the root message
        if properties:
            root = Artemis.find_root_key(mbox)
            msg = mbox[root]
            for property, value in properties:
                if property in msg:
                    msg.replace_header(property, value)
                else:
                    msg.add_header(property, value)
            mbox[root] = msg

        mbox.close()

        if opts['commit']:
            commands.commit(ui, repo, issue_fn)

        # If adding issue, add the new mailbox to the repository
        if not id:
            ui.status('Added new issue %s\n' % issue_id)
        else:
            Artemis.show_mbox(ui, mbox, 0)
