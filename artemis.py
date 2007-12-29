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
		print "%s [%s]: %s (%d)" % (issue[len(issues_path)+1:], # +1 for trailing /
									mbox[0]['State'],
									mbox[0]['Subject'], 
									len(mbox)-1)				# number of replies (-1 for self)
	

def add(ui, repo):
	"""Adds a new issue"""
	
	# First, make sure issues have a directory
	issues_path = os.path.join(repo.root, issues_dir)
	if not os.path.exists(issues_path): os.mkdir(issues_path)
	
	user = ui.username()

	default_issue_text  = 	"From: %s\nDate: %s\n" % (user,
													  time.strftime(date_format))
	default_issue_text += 	"State: %s\nSubject: brief description\n\n" % default_state
	default_issue_text += 	"Detailed description."

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
	issue_fn = issues_path
	while os.path.exists(issue_fn):
		issue_id = "%x" % random.randint(2**63, 2**64-1)
		issue_fn = os.path.join(issues_path, issue_id)
	msg.add_header('Message-Id', "%s-0-artemis@%s" % (issue_id, socket.gethostname()))

	# Add message to the mailbox
	mbox = mailbox.mbox(issue_fn)
	mbox.add(msg)
	mbox.close()

	# Add the new mailbox to the repository
	repo.add([issue_fn[(len(repo.root)+1):]])			# +1 for the trailing /


def show(ui, repo, id, comment = None):
	"""Shows issue ID, or possibly its comment COMMENT"""
	
	issue = _find_issue(ui, repo, id)
	if not issue: return

	# Read the issue
	mbox = mailbox.mbox(issue)
	msg = mbox[0]
	ui.write(msg.as_string())

	# Walk the mailbox, and output comments



def update(ui, repo, id, **opts):
	"""Update properties of issue ID, or add a comment to it or its comment COMMENT"""

	issue = _find_issue(ui, repo, id)
	if not issue: return

	properties = _get_properties(opts['property'])
	
	# Read the issue
	mbox = mailbox.mbox(issue)
	msg = mbox[0]

	# Fix the properties
	for property, value in properties:
		msg.replace_header(property, value)
	mbox[0] = msg
	mbox.flush()

	# Deal with comments

	# Show updated message
	ui.write(mbox[0].as_string())


def _find_issue(ui, repo, id):
	issues_path = os.path.join(repo.root, issues_dir)
	if not os.path.exists(issues_path): return False

	issues = glob.glob(os.path.join(issues_path, id + '*'))

	if len(issues) == 0:
		return False
	elif len(issues) > 1:
		ui.status("Multiple choices:\n")
		for i in issues: ui.status('  ', i[len(issues_path)+1:], '\n')
		return False
	
	return issues[0]

def _get_properties(property_list):
	return [p.split('=') for p in property_list]
	


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
				 _('hg iadd')),
	'ishow':  	(show, 
				 [('v', 'verbose', None, 'list the comments')], 
				 _('hg ishow ID [COMMENT]')),
	'iupdate':	(update,
				 [('p', 'property', [], 
				   'update properties (e.g., -p state=fixed)'),
				  ('c', 'comment', 0,
				   'add a comment to issue or its comment COMMENT')],
				 _('hg iupdate [OPTIONS] ID [COMMENT]'))
}
