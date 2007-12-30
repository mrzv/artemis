# Author: Dmitriy Morozov <hg@foxcub.org>, 2007

"""A very simple and lightweight issue tracker for Mercurial."""

from mercurial import hg, util
from mercurial.i18n import _
import os, time, random, mailbox, glob, socket


new_state = "new"
default_state = new_state
issues_dir = ".issues"
filter_filename = ".filters"
date_format = '%a, %d %b %Y %H:%M:%S %Z'


def list(ui, repo, **opts):
	"""List issues associated with the project"""

	# Process options
	show_all = False or opts['all']
	properties = _get_properties(opts['property']) or [['state', new_state]]
	date_match = lambda x: True
	if opts['date']: 
		date_match = util.matchdate(opts['date'])

	# Find issues
	issues_path = os.path.join(repo.root, issues_dir)
	if not os.path.exists(issues_path): return

	issues = glob.glob(os.path.join(issues_path, '*'))
	
	for issue in issues:
		mbox = mailbox.mbox(issue)
		property_match = True
		for property,value in properties: 
			property_match = property_match and (mbox[0][property] == value)
		if not show_all and not property_match: continue
		if not date_match(util.parsedate(mbox[0]['date'], [date_format])[0]): continue
		print "%s (%d) [%s]: %s" % (issue[len(issues_path)+1:], # +1 for trailing /
									len(mbox)-1,				# number of replies (-1 for self)
									mbox[0]['State'],
									mbox[0]['Subject'])
	

def add(ui, repo, id = None, comment = 0):
	"""Adds a new issue, or comment to an existing issue ID or its comment COMMENT"""
	
	comment = int(comment)

	# First, make sure issues have a directory
	issues_path = os.path.join(repo.root, issues_dir)
	if not os.path.exists(issues_path): os.mkdir(issues_path)

	if id:
		issue_fn, issue_id = _find_issue(ui, repo, id)
		if not issue_fn: 
			ui.warn('No such issue')
			return
	
	user = ui.username()

	default_issue_text  = 		"From: %s\nDate: %s\n" % (user, time.strftime(date_format))
	if not id: 
		default_issue_text += 	"State: %s\n" % default_state
	default_issue_text +=		"Subject: brief description\n\n"
	default_issue_text += 		"Detailed description."

	issue = ui.edit(default_issue_text, user)
	if issue.strip() == '':
		ui.warn('Empty issue, ignoring\n')
		return
	if issue.strip() == default_issue_text:
		ui.warn('Unchanged issue text, ignoring\n')
		return

	# Create the message
	msg = mailbox.mboxMessage(issue)
	msg.set_from('artemis', True)
	
	# Pick random filename
	if not id:
		issue_fn = issues_path
		while os.path.exists(issue_fn):
			issue_id = "%x" % random.randint(2**63, 2**64-1)
			issue_fn = os.path.join(issues_path, issue_id)
	# else: issue_fn already set

	# Add message to the mailbox
	mbox = mailbox.mbox(issue_fn)
	if id and comment not in mbox: 
		ui.warn('No such comment number in mailbox, commenting on the issue itself\n')
	if not id:
		msg.add_header('Message-Id', "%s-0-artemis@%s" % (issue_id, socket.gethostname()))
	else:
		msg.add_header('Message-Id', "%s-%d-artemis@%s" % (issue_id, len(mbox), socket.gethostname()))
		msg.add_header('References', mbox[(comment < len(mbox) and comment) or 0]['Message-Id'])
	mbox.add(msg)
	mbox.close()

	# If adding issue, add the new mailbox to the repository
	if not id: 
		repo.add([issue_fn[(len(repo.root)+1):]])			# +1 for the trailing /
		ui.status('Added new issue %s\n' % issue_id)


def show(ui, repo, id, comment = 0, **opts):
	"""Shows issue ID, or possibly its comment COMMENT"""
	
	comment = int(comment)
	issue, id = _find_issue(ui, repo, id)
	if not issue: return
	mbox = mailbox.mbox(issue)

	if opts['all']:
		ui.write('='*70 + '\n')
		for i in xrange(len(mbox)):
			_write_message(ui, mbox[i], i)
			ui.write('-'*70 + '\n')
		return

	_show_mbox(ui, mbox, comment)


def update(ui, repo, id, **opts):
	"""Update properties of issue ID"""

	issue, id = _find_issue(ui, repo, id)
	if not issue: return

	properties = _get_properties(opts['property'])
	
	# Read the issue
	mbox = mailbox.mbox(issue)
	msg = mbox[0]

	# Fix the properties
	properties_text = ''
	for property, value in properties:
		msg.replace_header(property, value)
		properties_text += '%s=%s\n' % (property, value)
	mbox[0] = msg

	# Write down a comment about updated properties
	if properties and not opts['no_property_comment']:
		user = ui.username()
		properties_text  = 	"From: %s\nDate: %s\nSubject: properties changes %s\n\n%s" % (user, time.strftime(date_format),
							 [property for property, value in properties], 
							 properties_text)
		msg = mailbox.mboxMessage(properties_text)
		msg.add_header('Message-Id', "%s-%d-artemis@%s" % (id, len(mbox), socket.gethostname()))
		msg.add_header('References', mbox[0]['Message-Id'])
		mbox.add(msg)
	mbox.flush()

	# Show updated message
	_show_mbox(ui, mbox, 0)


def _find_issue(ui, repo, id):
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
	
def _write_message(ui, message, index = 0):
	if index: ui.write("Comment: %d\n" % index)
	if ui.verbose:
		ui.write(message.as_string().strip() + '\n')
	else:
		if 'From' in message: ui.write('From: %s\n' % message['From'])
		if 'Date' in message: ui.write('Date: %s\n' % message['Date'])
		if 'Subject' in message: ui.write('Subject: %s\n' % message['Subject'])
		if 'State' in message: ui.write('State: %s\n' % message['State'])
		ui.write('\n' + message.get_payload().strip() + '\n')

def _show_mbox(ui, mbox, comment):
	# Output the issue (or comment)
	if comment >= len(mbox): 
		comment = 0
		ui.warn('Comment out of range, showing the issue itself\n')
	msg = mbox[comment]
	ui.write('='*70 + '\n')
	if comment:
		ui.write('Subject: %s\n' % mbox[0]['Subject'])
		ui.write('State: %s\n' % mbox[0]['State'])
		ui.write('-'*70 + '\n')
	_write_message(ui, msg, comment)
	ui.write('-'*70 + '\n')

	# Read the mailbox into the messages and children dictionaries
	messages = {}
	children = {}
	for i in xrange(len(mbox)):
		m = mbox[i]
		messages[m['Message-Id']] = (i,m)
		children.setdefault(m['References'], []).append(m['Message-Id'])
	children[None] = []				# Safeguard against infinte loop on empty Message-Id

	# Iterate over children
	id = msg['Message-Id'] 
	id_stack = (id in children and map(lambda x: (x, 1), reversed(children[id]))) or []
	if not id_stack: return
	ui.write('Comments:\n')
	while id_stack:
		id,offset = id_stack.pop()
		id_stack += (id in children and map(lambda x: (x, offset+1), reversed(children[id]))) or []
		index, msg = messages[id]
		ui.write('  '*offset + ('%d: ' % index) + msg['Subject'] + '\n')
	ui.write('-'*70 + '\n')


cmdtable = {
	'ilist':	(list, 
				 [('a', 'all', None, 
				   'list all issues (by default only those with state new)'),
				  ('p', 'property', [], 
				   'list issues with specific field values (e.g., -p state=fixed)'),
				  ('d', 'date', '', 'restrict to issues matching the date (e.g., -d ">12/28/2007)"'),
				  ('f', 'filter', '', 'restrict to pre-defined filter (in %s/%s)' % (issues_dir, filter_filename))], 
				 _('hg ilist [OPTIONS]')),
	'iadd':   	(add,  
				 [], 
				 _('hg iadd [ID] [COMMENT]')),
	'ishow':  	(show, 
				 [('a', 'all', None, 'list all comments')], 
				 _('hg ishow [OPTIONS] ID [COMMENT]')),
	'iupdate':	(update,
				 [('p', 'property', [], 
				   'update properties (e.g., -p state=fixed)'),
				  ('n', 'no-property-comment', None, 
				   'do not add a comment about changed properties')],
				 _('hg iupdate [OPTIONS] ID'))
}
