#!/usr/bin/env python

from mercurial import hg
from mercurial.i18n import _

def issues(ui, repo, **opts):
	"""Keep track of issues associated with the project"""
	if opts['list']:
		print "listing issues"
	elif opts['add']:
		print "adding issue"
	elif opts['show']:
		print "showing issue"
	elif opts['reply']:
		print "replying to issue"

cmdtable = {
	'issues':	(issues,
				 [('l', 'list', 	None, 	'list issues'),
				  ('a', 'add', 		None, 	'add issue'),
				  ('s', 'show', 	None, 	'show issue'),
				  ('r', 'reply', 	None,	'reply to issue')],
				 _('hg issues [OPTIONS]'))
}
