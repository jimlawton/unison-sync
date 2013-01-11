#!/usr/bin/env python
# Python script to automate running unison sync.

import os
import sys
import time
import argparse
import subprocess

APPNAME = "unison-sync"
CFGDIR = os.getenv("HOME") + '/.unison_sync'
LOGFILE = CFGDIR + '/unison_sync.log'

logfile = None

# TODO: Replace these with a config file.
SYNC_HOST = "saturn.cork.s3group.com"
# List of locations of local and remote locations.
syncpairs = [
    { "local": "/home/jiml/uhome", "remote": "ssh://%s//home/jiml" % SYNC_HOST }
]

def spawn(cmd):
    "Spawn a command, redirecting stdout and stderr to the logfile."

    status = None

    if opts.verbose:
        log("Executing: '%s'" % cmd)

    if logfile:
        status = subprocess.call([ cmd ], shell=True, stdout=logfile, stderr=logfile)
    else:
        os.system(cmd)

    return status


def log(msg, gui=False):
    "Print message to the logfile, and optionally pop up a GUI notification."

    if logfile:
        print >>logfile, msg
        logfile.flush()
    else:
        print msg

    if gui:
        os.system('notify-send "Unison Sync" "%s"' % msg)


def parseOpts():
    "Set up command-line option parsing."

    parser = argparse.ArgumentParser(description='Unison backup/sync utility.')
    parser.add_argument('-V', '--version', dest='version', action='store_true', help='display version')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='more detailed output')
    parser.add_argument('-s', '--single',  dest='single',  action='store_true', help='run once only')
    args = parser.parse_args()
    return args

def main():
    "Main function."

    global logfile
    global opts

    opts = parseOpts()
    
    # Only allow this program to run once!
    try:
        import socket
        s = socket.socket()
        host = socket.gethostname()
        port = 35636    # make sure this port is not used on this system
        s.bind((host, port))
    except:
        sys.exit(1)

    if not os.path.exists(CFGDIR):
        os.mkdir(CFGDIR)

    logfile = open(LOGFILE, 'a')

    unavail = False

    if not opts.single:
        log("Delaying start for 2 minutes...", gui=True)
        time.sleep(2 * 60)

    while 1:
        log("\n============ %s ============" % time.asctime())

        # Check if host is up.
        if spawn('ping -q -c 5 ' + SYNC_HOST) == 0:
            for syncpair in syncpairs:
                if not os.path.exists(syncpair["local"]):
                    log("Starting initial sync...", gui=True)
                    # NOTE: The trailing slash on the remote location is very important!
                    exit_code = spawn('rsync -raz ' + syncpair["remote"] + "/ " + syncpair["local"])
                    if exit_code != 0:
                        log("Could not sync! Aborting...", gui=True)
                        sys.exit(1)
                    log("Initial sync complete", gui=True)

            # Run Unison
            for syncpair in syncpairs:
                spawn('unison %s %s -batch -prefer newer -times=true' % (syncpair["local"], syncpair["remote"]))
                log("Sync of %s complete at %s" % (syncpair["local"], time.asctime()), gui=True)
        else:
            unavail = True

        if opts.single:
            break

        if unavail:
            log("Sync host unavailable! Sleeping for 30 minutes...", gui=True)
            time.sleep(30 * 60)
        else:
            time.sleep(120)


if __name__ == '__main__':
    main()
    sys.exit(0)
