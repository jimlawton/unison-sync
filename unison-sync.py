#!/usr/bin/env python
# Python script to automate running unison sync.

import os
import sys
import time
import argparse
import subprocess
import ConfigParser

_APPNAME = "unison-sync"
_UNISONDIR = os.path.join(HOME, '.unison')
_CFGDIR = os.path.join(os.getenv("HOME"), '.unison_sync')
_LOGFILE = os.path.join(_CFGDIR, 'unison_sync._log')
_CFGFILE = os.path.join(_CFGDIR, 'unison_sync._cfg')

_logfile = None
_cfgfile = None

_cfg = {}

# TODO: Replace these with a config file.
_cfg["host"] = "saturn.cork.s3group.com"
# List of locations of local and remote locations.
_cfg["pairs"] = [
    { "local": "/home/jiml/uhome", "remote": "ssh://%s//home/jiml" % _cfg["host"] }
]


def _writeDefaultConfig():
    "Write a default configuration file."
    config = ConfigParser.RawConfigParser()
    # When adding sections or items, add them in the reverse order of
    # how you want them to be displayed in the actual file.
    config.add_section('Pair1')
    config.set('Pair1', 'remote', 'EDIT_PUT_REMOTE_DIRECTORY_PATH_HERE')
    config.set('Pair1', 'local', 'EDIT_PUT_LOCAL_DIRECTORY_PATH_HERE')
    config.set('Pair1', 'host', 'EDIT_PUT_SSH_HOSTNAME_HERE')
    
    # Writing our configuration file to 'example._cfg'
    with open(_CFGFILE, 'wb') as configfile:
        config.write(configfile)


def _getConfig():
    "Get the configuration."
    if not os.path.exists(_CFGDIR):
        os.mkdir(_CFGDIR)
    if not os.path.exists(_CFGFILE):
        print "Warning: you must create a configuration file!"
        _writeDefaultConfig()
        print "A template for you to modify is in %s, please edit it and re-run unison-sync."
        sys.exit(1)
    else:
        config = ConfigParser.RawConfigParser()
        config.read(_CFGFILE)
        _cfg['host'] = config.get('Pair1', 'host')
        _cfg['pairs'] = [ { 'local': config.get('Pair1', 'local'), 'remote': config.get('Pair1', 'remote') } ]
        if _cfg['host'].startswith('EDIT_') or _cfg['pairs']['local'].startswith('EDIT_') or _cfg['pairs']['remote'].startswith('EDIT_'):
            print >>sys.stderr, "You must edit the configuration file (%s) and set the fields!" % (_CFGFILE)
            sys.exit(1)


def _spawn(cmd):
    "Spawn a command, redirecting stdout and stderr to the _logfile."

    status = None

    if opts.verbose:
        _log("Executing: '%s'" % cmd)

    if _logfile:
        status = subprocess.call([ cmd ], shell=True, stdout=_logfile, stderr=_logfile)
    else:
        os.system(cmd)

    return status


def _log(msg, gui=False):
    "Print message to the _logfile, and optionally pop up a GUI notification."

    if _logfile:
        print >>_logfile, msg
        _logfile.flush()
    else:
        print msg

    if gui:
        os.system('notify-send "Unison Sync" "%s"' % msg)


def _parseOpts():
    "Set up command-line option parsing."

    parser = argparse.ArgumentParser(description='Unison backup/sync utility.')
    parser.add_argument('-V', '--version', dest='version', action='store_true', help='display version')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='more detailed output')
    parser.add_argument('-s', '--single',  dest='single',  action='store_true', help='run once only')
    args = parser.parse_args()
    return args

def main():
    "Main function."

    global _logfile
    global opts

    opts = _parseOpts()
    
    # Only allow this program to run once!
    try:
        import socket
        s = socket.socket()
        host = socket.gethostname()
        port = 35636    # make sure this port is not used on this system
        s.bind((host, port))
    except:
        sys.exit(1)

    _getConfig()
    
    _logfile = open(_LOGFILE, 'a')

    unavail = False

    if not opts.single:
        _log("Delaying start for 2 minutes...", gui=True)
        time.sleep(2 * 60)

    while 1:
        _log("\n============ %s ============" % time.asctime())

        # Check if host is up.
        if _spawn('ping -q -c 5 ' + _cfg["synchost"]) == 0:
            for syncpair in _cfg["pairs"]:
                if not os.path.exists(syncpair["local"]):
                    _log("Starting initial sync...", gui=True)
                    # NOTE: The trailing slash on the remote location is very important!
                    exit_code = _spawn('rsync -raz ' + syncpair["remote"] + "/ " + syncpair["local"])
                    if exit_code != 0:
                        _log("Could not sync! Aborting...", gui=True)
                        sys.exit(1)
                    _log("Initial sync complete", gui=True)

            # Run Unison
            for syncpair in _cfg["pairs"]:
                _spawn('unison %s %s -batch -prefer newer -times=true' % (syncpair["local"], syncpair["remote"]))
                _log("Sync of %s complete at %s" % (syncpair["local"], time.asctime()), gui=True)
        else:
            unavail = True

        if opts.single:
            break

        if unavail:
            _log("Sync host unavailable! Sleeping for 30 minutes...", gui=True)
            time.sleep(30 * 60)
        else:
            time.sleep(120)


if __name__ == '__main__':
    main()
    sys.exit(0)
