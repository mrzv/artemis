import mailbox, glob, os.path, os
import artemis
from mercurial import ui, hg

repo = hg.repository(ui.ui())

issue_filenames = glob.glob(os.path.join(artemis.issues_dir, '*'))
for fn in issue_filenames:
    mb = mailbox.mbox(fn)
    messages = [m for m in mb]
    mb.close()
    os.unlink(fn)
    repo.remove([fn])
    md = mailbox.Maildir(fn)
    md.lock()
    keys = [md.add(m) for m in messages]
    md.close()
    for k in keys: repo.add([fn + '/new/' + k])
