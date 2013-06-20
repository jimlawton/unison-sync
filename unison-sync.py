#!/usr/bin/env python
# Python script to automate running unison sync.
#
# Put something like this into your ~/.bashrc:
#
# # Sync script... replace "apollo" with the name of your laptop.
# # Only run on the client host, and only if interactive.
# if [ "$HOSTNAME" == "apollo" ]; then
#     echo $- | grep -q i
#     if [ $? -eq 0 ]; then
#         sync_proc_count=`ps auxww | grep unison-sync.py | grep -vc grep`
#         if [ $sync_proc_count -eq 0 ]; then
#             python ${HOME}/Dropbox/unixhome/unison-sync.py >${HOME}/.unison_sync/unison_sync.log 2>&1 &
#         fi
#     fi
# fi

import os
import sys
import time
import argparse
import subprocess
import ConfigParser
import urlparse

_APPNAME = "unison-sync"
_UNISONDIR = os.path.join(os.getenv("HOME"), '.unison')
_UNISONCFG = os.path.join(_UNISONDIR, 'default.prf')
_CFGDIR = os.path.join(os.getenv("HOME"), '.unison_sync')
_LOGFILE = os.path.join(_CFGDIR, 'unison_sync.log')
_CFGFILE = os.path.join(_CFGDIR, 'unison_sync.cfg')

_DEFAULTS = { 'initdelay': 2, 'retry': 30 * 60, 'interval': 120 }

_logfile = None
_cfgfile = None

_cfg = {}

def _setupUnison():
    "Set up Unison configuration."
    
    if not os.path.exists(_UNISONDIR):
        os.mkdir(_UNISONDIR)
    if not os.path.exists(_UNISONCFG):
        with open(_UNISONCFG, 'wb') as unisoncfg:
            unisoncfg.write("""
# Unison preferences file
ignore = Name .nfs*
ignore = Name *~
ignore = Name .*~
ignore = Name *.tmp
ignore = Name lock
ignore = Name Cache
ignore = Name .cache
ignore = Name tmp
ignore = Name .tmp
ignore = Name temp
ignore = Name ssh*\@*
ignore = Name *.iso
ignore = Name .snapshot
ignore = Name .lastpass
ignore = Name .unison
ignore = Name .xsession-errors
ignore = Name .history
ignore = Name .Skype

# Ignore all Tbird summary files.
ignore = Regex \.thunderbird/.*\.msf

auto = true
batch = true
#silent = true
contactquietly = true
fastcheck = true
maxthreads = 50
#terse = true
addprefsto = default

# turn on ssh compression
sshargs = -C
""")


def _writeDefaultConfig():
    "Write a default configuration file."
    
    config = ConfigParser.RawConfigParser()
    
    config.add_section('General')
    for key in [ 'initdelay', 'retry', 'interval' ]:
        config.set('General', key, _DEFAULTS[key])
    
    config.add_section('Pair1')
    config.set('Pair1', 'local', 'EDIT_PUT_LOCAL_DIRECTORY_PATH_HERE')
    config.set('Pair1', 'remote', 'EDIT_PUT_REMOTE_DIRECTORY_PATH_HERE')
    
    with open(_CFGFILE, 'wb') as configfile:
        config.write(configfile)


def _getConfig():
    "Get the configuration."
    if not os.path.exists(_CFGDIR):
        os.mkdir(_CFGDIR)
    if not os.path.exists(_CFGFILE):
        print "Warning: you must create a configuration file!"
        _writeDefaultConfig()
        print "A template for you to modify is in %s, please edit it and re-run unison-sync." % (_CFGFILE)
        sys.exit(1)
    else:
        config = ConfigParser.RawConfigParser()
        config.read(_CFGFILE)
        for key in [ 'initdelay', 'retry', 'interval' ]:
            _cfg[key] = config.getint('General', key)
        
        # TODO: Eventually support multiple sync pairs, just one for now.
        _cfg['pairs'] = [ { 'local': config.get('Pair1', 'local'), 'remote': config.get('Pair1', 'remote'), 'rsync': config.get('Pair1', 'rsync') } ]
        if _cfg['pairs'][0]['local'].startswith('EDIT_') or _cfg['pairs'][0]['remote'].startswith('EDIT_'):
            print >>sys.stderr, "You must edit the configuration file (%s) and set the fields!" % (_CFGFILE)
            sys.exit(1)
        _cfg['pairs'][0]['host'] = urlparse.urlparse(_cfg['pairs'][0]['remote']).hostname


def _spawn(cmd):
    "Spawn a command, redirecting stdout and stderr to the logfile."

    status = None

    if opts.verbose:
        _log("Executing: '%s'" % cmd)

    if _logfile:
        status = subprocess.call([ cmd ], shell=True, stdout=_logfile, stderr=_logfile)
    else:
        os.system(cmd)

    return status


def _log(msg, gui=False, level='normal'):
    "Print message to the logfile, and optionally pop up a GUI notification."

    if _logfile:
        print >>_logfile, msg
        _logfile.flush()
    else:
        print msg

    if gui:
        os.system('notify-send -u %s "Unison Sync" "%s"' % (level, msg))


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

    _setupUnison()
    _getConfig()
    
    _logfile = open(_LOGFILE, 'a')

    unavail = False

    if not opts.single:
        _log("Delaying start for 2 minutes...", gui=True)
        time.sleep(_cfg['initdelay'])

    if _spawn('ssh-add -l >/dev/null') != 0:
        _log("ERROR: SSH agent not available, aborting...", gui=True, level='critical')
        sys.exit(1)

    while 1:
        _log("\n============ %s ============" % time.asctime())

        for syncpair in _cfg["pairs"]:
            
            # Check if host is up.
            if _spawn('ping -q -c 5 ' + syncpair["host"]) != 0:
                _log("Sync host unavailable!", gui=True, level='critical')
                unavail = True
                continue

            if not os.path.exists(syncpair["local"]):
                _log("Initial sync of %s started at %s" % (syncpair['local'], time.asctime()))
                _log("Initial sync of %s started..." % (syncpair['local']), gui=True)
                # NOTE: The trailing slash on the remote location is very important!
                exit_code = _spawn('rsync -raz ' + syncpair['rsync'] + "/ " + syncpair['local'])
                if exit_code != 0:
                    _log("Could not sync! Aborting...", gui=True, level='critical')
                    sys.exit(1)
                _log("Initial sync of %s complete at %s" % (syncpair['local'], time.asctime()))
                _log("Initial sync complete", gui=True)
                
            # Run Unison
            _log("Sync of %s started at %s" % (syncpair['local'], time.asctime()))
            status = _spawn('unison %s %s -batch -prefer newer -times=true' % (syncpair['local'], syncpair['remote']))
            if status != 0:
                _log("Sync of %s failed at %s" % (syncpair['local'], time.asctime()), gui=True, level='critical')
            else:
                _log("Sync of %s complete at %s" % (syncpair['local'], time.asctime()), gui=True)

        if opts.single:
            break

        if unavail:
            _log("Sync host unavailable! Sleeping for %d seconds..." % _cfg['retry'], gui=True, level='critical')
            time.sleep(_cfg['retry'])
        else:
            time.sleep(_cfg['interval'])


if __name__ == '__main__':
    main()
    sys.exit(0)
