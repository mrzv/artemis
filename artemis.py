#!/usr/bin/env python

from mercurial import hg
from mercurial.i18n import _
import os, time, random

def list(ui, repo, **opts):
	"""List issues associated with the project"""

def add(ui, repo):
	"""Adds a new issue"""
	
	# First, make sure issues have a directory
	issues_path = os.path.join(repo.root, '.issues')
	if not os.path.exists(issues_path): os.mkdir(issues_path)
	
	user = ui.username()

	default_issue_text = 	"From: %s\nDate: %s\n" % (user,
													  time.strftime('%a, %d %b %Y %H:%M:%S %Z'))
	default_issue_text += 	"Status: new\nSubject: brief description\n\n"
	default_issue_text += 	"Detailed description."

	issue = ui.edit(default_issue_text, user)
	if issue.strip() == '':
		ui.warn('Empty issue, ignoring\n')
		return
	if issue.strip() == default_issue_text:
		ui.warn('Unchanged issue text, ignoring\n')
		return

	# Pick random filename
	issue_fn = issues_path
	while os.path.exists(issue_fn):
		issue_fn = os.path.join(issues_path, "%x" % random.randint(2**32, 2**64-1))

	# FIXME: replace with creating a mailbox
	f =	file(issue_fn, "w")
	f.write(issue)
	f.close()

	repo.add([issue_fn[(len(repo.root)+1):]])			# +1 for the trailing /

def show(ui, repo, id):
	"""Shows issue ID"""

cmdtable = {
	'issues-list':	(list, 
					 [('s', 'status', None, 'restrict status')], 
					 _('hg issues-list')),
	'issues-add':   (add,  
					 [], 
					 _('hg issues-add')),
	'issues-show':  (show, 
					 [], 
					 _('hg issues-show ID'))
}
