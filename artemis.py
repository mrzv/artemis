# Author: Dmitriy Morozov <hg@foxcub.org>, 2007 -- 2009

"""A very simple and lightweight issue tracker for Mercurial."""

from mercurial import hg, util
from mercurial.i18n import _
import os, time, random, mailbox, glob, socket, ConfigParser
import mimetypes
from email import encoders
from email.generator import Generator
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


state = {'new': 'new', 'fixed': ['fixed', 'resolved']}
state['default'] = state['new']
default_issues_dir = ".issues"
filter_prefix = ".filter"
date_format = '%a, %d %b %Y %H:%M:%S %1%2'
maildir_dirs = ['new','cur','tmp']


def ilist(ui, repo, **opts):
    """List issues associated with the project"""

    # Process options
    show_all = opts['all']
    properties = []
    match_date, date_match = False, lambda x: True
    if opts['date']:
        match_date, date_match = True, util.matchdate(opts['date'])

    # Find issues
    issues_dir = ui.config('artemis', 'issues', default = default_issues_dir)
    issues_path = os.path.join(repo.root, issues_dir)
    if not os.path.exists(issues_path): return

    issues = glob.glob(os.path.join(issues_path, '*'))

    _create_all_missing_dirs(issues_path, issues)

    # Process filter
    if opts['filter']:
        filters = glob.glob(os.path.join(issues_path, filter_prefix + '*'))
        config = ConfigParser.SafeConfigParser()
        config.read(filters)
        if not config.has_section(opts['filter']):
            ui.write('No filter %s defined\n' % opts['filter'])
        else:
            properties += config.items(opts['filter'])

    cmd_properties = _get_properties(opts['property'])
    list_properties = [p[0] for p in cmd_properties if len(p) == 1]
    list_properties_dict = {}
    properties += filter(lambda p: len(p) > 1, cmd_properties)

    for issue in issues:
        mbox = mailbox.Maildir(issue, factory=mailbox.MaildirMessage)
        root = _find_root_key(mbox)
        property_match = True
        for property,value in properties:
            if value:
                property_match = property_match and (mbox[root][property] == value)
            else:
                property_match = property_match and (property not in mbox[root])

        if not show_all and (not properties or not property_match) and (properties or mbox[root]['State'].upper() in [f.upper() for f in state['fixed']]): continue
        if match_date and not date_match(util.parsedate(mbox[root]['date'])[0]): continue

        if not list_properties:
            ui.write("%s (%3d) [%s]: %s\n" % (issue[len(issues_path)+1:], # +1 for trailing /
                                              len(mbox)-1,                # number of replies (-1 for self)
                                              _status_msg(mbox[root]),
                                              mbox[root]['Subject']))
        else:
            for lp in list_properties:
                if lp in mbox[root]:    list_properties_dict.setdefault(lp, set()).add(mbox[root][lp])

    if list_properties:
        for lp in list_properties_dict.keys():
            ui.write("%s:\n" % lp)
            for value in sorted(list_properties_dict[lp]):
                ui.write("  %s\n" % value)


def iadd(ui, repo, id = None, comment = 0, **opts):
    """Adds a new issue, or comment to an existing issue ID or its comment COMMENT"""

    comment = int(comment)

    # First, make sure issues have a directory
    issues_dir = ui.config('artemis', 'issues', default = default_issues_dir)
    issues_path = os.path.join(repo.root, issues_dir)
    if not os.path.exists(issues_path): os.mkdir(issues_path)

    if id:
        issue_fn, issue_id = _find_issue(ui, repo, id)
        if not issue_fn:
            ui.warn('No such issue\n')
            return
        _create_missing_dirs(issues_path, issue_id)

    user = ui.username()

    default_issue_text  =         "From: %s\nDate: %s\n" % (user, util.datestr(format = date_format))
    if not id:
        default_issue_text +=     "State: %s\n" % state['default']
    default_issue_text +=         "Subject: brief description\n\n"
    default_issue_text +=         "Detailed description."

    # Get properties, and figure out if we need an explicit comment
    properties = _get_properties(opts['property'])
    no_comment = id and properties and opts['no_property_comment']
    message = opts['message']

    # Create the text
    if message:
        if not id:
            state_str = 'State: %s\n' % state['default']
        else:
            state_str = ''
        issue = "From: %s\nDate: %s\nSubject: %s\n%s" % \
                (user, util.datestr(format=date_format), message, state_str)
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
        properties_subject = ', '.join(['%s=%s' % (property, value) for (property, value) in properties])

        issue =     "From: %s\nDate: %s\nSubject: changed properties (%s)\n" % \
                     (user, util.datestr(format = date_format), properties_subject)

    # Create the message
    msg = mailbox.MaildirMessage(issue)
    if opts['attach']:
        outer = _attach_files(msg, opts['attach'])
    else:
        outer = msg

    # Pick random filename
    if not id:
        issue_fn = issues_path
        while os.path.exists(issue_fn):
            issue_id = _random_id()
            issue_fn = os.path.join(issues_path, issue_id)
    # else: issue_fn already set

    # Add message to the mailbox
    mbox = mailbox.Maildir(issue_fn, factory=mailbox.MaildirMessage)
    keys = _order_keys_date(mbox)
    mbox.lock()
    if id and comment >= len(mbox):
        ui.warn('No such comment number in mailbox, commenting on the issue itself\n')

    if not id:
        outer.add_header('Message-Id', "<%s-0-artemis@%s>" % (issue_id, socket.gethostname()))
    else:
        root = keys[0]
        outer.add_header('Message-Id', "<%s-%s-artemis@%s>" % (issue_id, _random_id(), socket.gethostname()))
        outer.add_header('References', mbox[(comment < len(mbox) and keys[comment]) or root]['Message-Id'])
        outer.add_header('In-Reply-To', mbox[(comment < len(mbox) and keys[comment]) or root]['Message-Id'])
    repo.add([issue_fn[(len(repo.root)+1):] + '/new/'  + mbox.add(outer)])   # +1 for the trailing /

    # Fix properties in the root message
    if properties:
        root = _find_root_key(mbox)
        msg = mbox[root]
        for property, value in properties:
            if property in msg:
                msg.replace_header(property, value)
            else:
                msg.add_header(property, value)
        mbox[root] = msg

    mbox.close()

    # If adding issue, add the new mailbox to the repository
    if not id:
        ui.status('Added new issue %s\n' % issue_id)
    else:
        _show_mbox(ui, mbox, 0)

def ishow(ui, repo, id, comment = 0, **opts):
    """Shows issue ID, or possibly its comment COMMENT"""

    comment = int(comment)
    issue, id = _find_issue(ui, repo, id)
    if not issue:
        return ui.warn('No such issue\n')
    
    issues_dir = ui.config('artemis', 'issues', default = default_issues_dir)
    _create_missing_dirs(os.path.join(repo.root, issues_dir), issue)

    if opts.get('mutt'):
        return util.system('mutt -R -f %s' % issue)

    mbox = mailbox.Maildir(issue, factory=mailbox.MaildirMessage)

    if opts['all']:
        ui.write('='*70 + '\n')
        i = 0
        keys = _order_keys_date(mbox)
        for k in keys:
            _write_message(ui, mbox[k], i, skip = opts['skip'])
            ui.write('-'*70 + '\n')
            i += 1
        return

    _show_mbox(ui, mbox, comment, skip = opts['skip'])

    if opts['extract']:
        attachment_numbers = map(int, opts['extract'])
        keys = _order_keys_date(mbox)
        msg = mbox[keys[comment]]
        counter = 1
        for part in msg.walk():
            ctype = part.get_content_type()
            maintype, subtype = ctype.split('/', 1)
            if maintype == 'multipart' or ctype == 'text/plain': continue
            if counter in attachment_numbers:
                filename = part.get_filename()
                if not filename:
                    ext = mimetypes.guess_extension(part.get_content_type()) or ''
                    filename = 'attachment-%03d%s' % (counter, ext)
                fp = open(filename, 'wb')
                fp.write(part.get_payload(decode = True))
                fp.close()
            counter += 1


def _find_issue(ui, repo, id):
    issues_dir = ui.config('artemis', 'issues', default = default_issues_dir)
    issues_path = os.path.join(repo.root, issues_dir)
    if not os.path.exists(issues_path): return False

    issues = glob.glob(os.path.join(issues_path, id + '*'))

    if len(issues) == 0:
        return False, 0
    elif len(issues) > 1:
        ui.status("Multiple choices:\n")
        for i in issues: ui.status('  ', i[len(issues_path)+1:], '\n')
        return False, 0

    return issues[0], issues[0][len(issues_path)+1:]

def _get_properties(property_list):
    return [p.split('=') for p in property_list]

def _write_message(ui, message, index = 0, skip = None):
    if index: ui.write("Comment: %d\n" % index)
    if ui.verbose:
        _show_text(ui, message.as_string().strip(), skip)
    else:
        if 'From' in message: ui.write('From: %s\n' % message['From'])
        if 'Date' in message: ui.write('Date: %s\n' % message['Date'])
        if 'Subject' in message: ui.write('Subject: %s\n' % message['Subject'])
        if 'State' in message: ui.write('State: %s\n' % message['State'])
        counter = 1
        for part in message.walk():
            ctype = part.get_content_type()
            maintype, subtype = ctype.split('/', 1)
            if maintype == 'multipart': continue
            if ctype == 'text/plain':
                ui.write('\n')
                _show_text(ui, part.get_payload().strip(), skip)
            else:
                filename = part.get_filename()
                ui.write('\n' + '%d: Attachment [%s, %s]: %s' % (counter, ctype, _humanreadable(len(part.get_payload())), filename) + '\n')
                counter += 1

def _show_text(ui, text, skip = None):
    for line in text.splitlines():
        if not skip or not line.startswith(skip):
            ui.write(line + '\n')
    ui.write('\n')

def _show_mbox(ui, mbox, comment, **opts):
    # Output the issue (or comment)
    if comment >= len(mbox):
        comment = 0
        ui.warn('Comment out of range, showing the issue itself\n')
    keys = _order_keys_date(mbox)
    root = keys[0]
    msg = mbox[keys[comment]]
    ui.write('='*70 + '\n')
    if comment:
        ui.write('Subject: %s\n' % mbox[root]['Subject'])
        ui.write('State: %s\n' % mbox[root]['State'])
        ui.write('-'*70 + '\n')
    _write_message(ui, msg, comment, skip = ('skip' in opts) and opts['skip'])
    ui.write('-'*70 + '\n')

    # Read the mailbox into the messages and children dictionaries
    messages = {}
    children = {}
    i = 0
    for k in keys:
        m = mbox[k]
        messages[m['Message-Id']] = (i,m)
        children.setdefault(m['In-Reply-To'], []).append(m['Message-Id'])
        i += 1
    children[None] = []                # Safeguard against infinte loop on empty Message-Id

    # Iterate over children
    id = msg['Message-Id']
    id_stack = (id in children and map(lambda x: (x, 1), reversed(children[id]))) or []
    if not id_stack: return
    ui.write('Comments:\n')
    while id_stack:
        id,offset = id_stack.pop()
        id_stack += (id in children and map(lambda x: (x, offset+1), reversed(children[id]))) or []
        index, msg = messages[id]
        ui.write('  '*offset + '%d: [%s] %s\n' % (index, util.shortuser(msg['From']), msg['Subject']))
    ui.write('-'*70 + '\n')

def _find_root_key(maildir):
    for k,m in maildir.iteritems():
        if 'in-reply-to' not in m:
            return k

def _order_keys_date(mbox):
    keys = mbox.keys()
    root = _find_root_key(mbox)
    keys.sort(lambda k1,k2: -(k1 == root) or cmp(util.parsedate(mbox[k1]['date']), util.parsedate(mbox[k2]['date'])))
    return keys

def _random_id():
    return "%x" % random.randint(2**63, 2**64-1)

def _create_missing_dirs(issues_path, issue):
    for d in maildir_dirs:
        path = os.path.join(issues_path,issue,d)
        if not os.path.exists(path): os.mkdir(path)

def _create_all_missing_dirs(issues_path, issues):
    for i in issues:
        _create_missing_dirs(issues_path, i)

def _humanreadable(size):
    if size > 1024*1024:
        return '%5.1fM' % (float(size) / (1024*1024))
    elif size > 1024:
        return '%5.1fK' % (float(size) / 1024)
    else:
        return '%dB' % size

def _attach_files(msg, filenames):
    outer = MIMEMultipart()
    for k in msg.keys(): outer[k] = msg[k]
    outer.attach(MIMEText(msg.get_payload()))

    for filename in filenames:
        ctype, encoding = mimetypes.guess_type(filename)
        if ctype is None or encoding is not None:
            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.
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
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        outer.attach(attachment)
    return outer

def _status_msg(msg):
    if msg['State'] == 'resolved':
        return 'resolved=' + msg['resolution']
    else:
        return msg['State']

cmdtable = {
    'ilist':    (ilist,
                 [('a', 'all', False,
                   'list all issues (by default only those with state new)'),
                  ('p', 'property', [],
                   'list issues with specific field values (e.g., -p state=fixed); lists all possible values of a property if no = sign'),
                  ('d', 'date', '', 'restrict to issues matching the date (e.g., -d ">12/28/2007)"'),
                  ('f', 'filter', '', 'restrict to pre-defined filter (in %s/%s*)' % (default_issues_dir, filter_prefix))],
                 _('hg ilist [OPTIONS]')),
    'iadd':       (iadd,
                 [('a', 'attach', [],
                   'attach file(s) (e.g., -a filename1 -a filename2)'),
                  ('p', 'property', [],
                   'update properties (e.g., -p state=fixed)'),
                  ('n', 'no-property-comment', None,
                   'do not add a comment about changed properties'),
                  ('m', 'message', '',
                   'use <text> as an issue subject')],
                 _('hg iadd [OPTIONS] [ID] [COMMENT]')),
    'ishow':      (ishow,
                 [('a', 'all', None, 'list all comments'),
                  ('s', 'skip', '>', 'skip lines starting with a substring'),
                  ('x', 'extract', [], 'extract attachments (provide attachment number as argument)'),
                  ('', 'mutt', False, 'use mutt to show issue')],
                 _('hg ishow [OPTIONS] ID [COMMENT]')),
}

# vim: expandtab
