#!/usr/bin/env python

from mercurial.util import parsedate, datestr
import glob, mailbox

issues = glob.glob('.issues/*')

for i in issues:
	mbox=mailbox.mbox(i)
	for k in xrange(len(mbox)):
		msg = mbox[k]
		print msg['Date']
		d = parsedate(msg['Date'], ['%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S'])
		print d
		print datestr(d, '%a, %d %b %Y %H:%M:%S')
		msg.replace_header('Date', datestr(d, '%a, %d %b %Y %H:%M:%S'))
		mbox[k] = msg
	mbox.flush()
