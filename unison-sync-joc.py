#!/usr/bin/env python
# Python script to automate running unison sync.
#
# Put this in your ~/.bashrc:
#
# Sync script... replace "apollo" with the name of your laptop.
# if [ "$HOSTNAME" == "apollo" ]; then
#     python ${HOME}/Dropbox/unixhome/unison-sync.py >${HOME}/.unison_sync/unison_sync.log 2>&1 &
# fi

import os
import sys
import time

HOME = os.getenv("HOME")
CFGDIR = HOME + '/.unison_sync'
UNISONDIR = HOME + "/.unison"

# Replace "saturn" with the name of your desktop.
SYNC_HOST = "oxygen.cork.s3group.com"
USER_NAME = "johnoc"

UNISON_REMOTE = "ssh://%s/%s" % (SYNC_HOST, HOME)

# List of locations of local and remote locations.
syncpairs = [
    { "local": HOME + "/uhome", "remote": "%s@%s:%s" % (USER_NAME, SYNC_HOST, HOME) }
]

# Only allow this program to run once!
try:
    import socket
    s = socket.socket()
    #host = socket.gethostname()
    port = 35638    # make sure this port is not used on this system
    s.bind(('localhost', port))
except:
    sys.exit(1)

if not os.path.exists(CFGDIR):
    os.mkdir(CFGDIR)

if not os.path.exists(UNISONDIR):
    os.mkdir(UNISONDIR)
    f = open(UNISONDIR + "/default.prf", 'w')
    f.write("""
# Unison preferences file
ignore = Name .nfs*
ignore = Name *~
ignore = Name .*~
ignore = Name *.tmp
ignore = Name lock
ignore = Name Cache
ignore = Name .cache
ignore = Name tmp
ignore = Name temp
ignore = Name ssh*\@*
ignore = Name *.iso
ignore = Name .snapshot
ignore = Name .unison\*

auto = true
batch = true
#silent = true
#contactquietly = true
fastcheck = true
maxthreads = 50
#terse = true
addprefsto = default

# turn on ssh compression
sshargs = -C
""")
    f.close()

while 1:
    # Check if host is up.
    if os.system('ping -c 1 ' + SYNC_HOST) == 0:

        for syncpair in syncpairs:
            if not os.path.exists(syncpair["local"]):
                os.system('notify-send -t 500 "Unison Sync" "Starting initial sync..."')
                # NOTE: The trailing slash on the remote location is very important!

		print 'rsync -raz -e ssh ' + syncpair["remote"] + "/ " + syncpair["local"]

                exit_code = os.system('rsync -raz ' + syncpair["remote"] + "/ " + syncpair["local"])
                if exit_code != 0:
                    os.system('notify-send -t 500 "Unison Sync" "Could not sync!"')
                    sys.exit(1)
                os.system('notify-send -t 500 "Unison Sync" "Initial sync complete"')

        # Run Unison
        for syncpair in syncpairs:
            os.system('unison %s %s -ui text -batch -prefer newer -ignorearchives -times=true' % (syncpair["local"], UNISON_REMOTE))
            #os.system('notify-send -t 500 "Unison Sync" "Sync of %s complete"' % (syncpair["local"]))

    else:
        os.system('notify-send -t 500 "Unison Sync" "Sync host unavailable!"')
    time.sleep(120)

sys.exit(0)

