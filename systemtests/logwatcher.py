#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
#
# This file derived from CTS.py in the Linux-HA project.
# That file written and copyrighted (2000, 2001) by Alan Robertson.
# The owner contributed it to the Assimilation Project [and Assimilation Systems Limited]
# in August 2014.
# That original file was created and copyrighted before he joined IBM and was excluded
# from his IP agreement with IBM.  The first version was written before he
# joined SuSE as it was the earliest component of the CTS testing system for Linux-HA.
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
'''
This module defines the most excellent LogWatcher class - useful for watching logs
and curing what ails you ;-)
'''
import os, re, time

# R0902: too many instance attributes
# pylint: disable=R0902
class LogWatcher(object):

    '''This class watches logs for messages that fit certain regular
       expressions.  Watching logs for events isn't the ideal way
       to do business, but it's better than nothing :-)

       On the other hand, this class is really pretty cool ;-)

       The way you use this class is as follows:
          Construct a LogWatcher object
          Call setwatch() when you want to start watching the log
          Call look() to scan the log looking for the patterns
            or call lookforall() to locate them all
    '''

    def __init__(self, log, regexes, timeout=10, debug=None, returnonlymatch=False):
        '''This is the constructor for the LogWatcher class.  It takes a
        log name to watch, and a list of regular expressions to watch for."

        @FIXME: should store the compiled regexes - no point in waiting around
        until later.
        '''

        #  Validate our arguments.  Better sooner than later ;-)
        for regex in regexes:
            assert re.compile(regex)
        self.regexes = regexes
        self.filename = log
        self.debug=debug
        self.returnonlymatch = returnonlymatch
        self.whichmatched = -1
        self.unmatched = None
        self.st_ino = None
        self.st_dev = None
        self.logfile = None
        self.size = None
        if self.debug:
            print "Debug now on for for log", log
        self.Timeout = int(timeout)
        if not os.access(log, os.R_OK):
            raise ValueError("File [" + log + "] not accessible (r)")

    def setwatch(self, frombeginning=False):
        '''Mark the place to start watching the log from.
        '''
        self.logfile = open(self.filename, "r")
        self.size = os.path.getsize(self.filename)
        fsinfo = os.stat(self.filename)
        self.st_dev = fsinfo.st_dev
        self.st_ino = fsinfo.st_ino
        if not frombeginning:
            self.logfile.seek(0,2)

    def ReturnOnlyMatch(self, onlymatch=True):
        '''Set the ReturnOnlyMatch flag
        '''
        self.returnonlymatch = onlymatch

    # FIXME: many branches (R0912)?
    # pylint: disable=R0912
    def look(self, timeout=None):
        '''Examine the log looking for the given patterns.
        It starts looking from the place marked by setwatch().
        This function looks in the file in the fashion of tail -f.
        It properly recovers from log file truncation, and it should
        recover from removing and recreating the log as well.

        We return the first line which matches any of our patterns.
        '''
        last_line=None
        first_line=None
        if timeout == None:
            timeout = self.Timeout

        done=time.time()+timeout+1
        if self.debug:
            print "starting search: timeout=%d" % timeout
            for regex in self.regexes:
                print "Looking for regex: ", regex

        while (timeout <= 0 or time.time() <= done):
            newsize=os.path.getsize(self.filename)
            if self.debug > 4:
                print "newsize = %d" % newsize
            if newsize < self.size:
                # Somebody truncated the log!
                if self.debug:
                    print "Log truncated!"
                self.setwatch(frombeginning=True)
                continue
            if newsize > self.logfile.tell():
                line=self.logfile.readline()
                if self.debug > 2:
                    print "Looking at line:", line
                if line:
                    last_line=line
                    if not first_line:
                        first_line=line
                        if self.debug:
                            print "First line: "+ line
                    which=-1
                    for regex in self.regexes:
                        which=which+1
                        if self.debug > 3:
                            print "Comparing line to ", regex
                        #matchobj = re.search(string.lower(regex), string.lower(line))
                        matchobj = re.search(regex, line)
                        if matchobj:
                            self.whichmatched=which
                            if self.returnonlymatch:
                                return matchobj.group(self.returnonlymatch)
                            else:
                                if self.debug:
                                    print "Returning line"
                                return line
            else: # make sure the file hasn't been recreated...
                fsinfo = os.stat(self.filename)
                if fsinfo.st_dev != self.st_dev or fsinfo.st_ino != self.st_ino:
                    if self.debug:
                        print "Log file %s recreated!" % self.filename
                    self.setwatch(frombeginning=True)

            newsize=os.path.getsize(self.filename)
            if self.logfile.tell() == newsize:
                if timeout > 0:
                    time.sleep(0.025)
                else:
                    if self.debug:
                        print "End of file"
                        print "Last line: "+last_line
                    return None
        if self.debug:
            print "Timeout"
            print "Last line: "+last_line
        return None

    def lookforall(self, timeout=None):
        '''Examine the log looking for ALL of the given patterns.
        It starts looking from the place marked by setwatch().

        We return when the timeout is reached, or when we have found
        ALL of the regexes that were part of the watch
        Note that the order of the REGEXes is not relevant.  They can
        be occur in the logs in any order.  Hope that's what you wanted ;-)
        '''

        if timeout == None:
            timeout = self.Timeout
        save_regexes = self.regexes
        returnresult = []
        while (len(self.regexes) > 0):
            oneresult = self.look(timeout)
            if not oneresult:
                self.unmatched = self.regexes
                self.regexes = save_regexes
                return None
            returnresult.append(oneresult)
            del self.regexes[self.whichmatched]
        self.unmatched = None
        self.regexes = save_regexes
        return returnresult

# In case we ever want multiple regexes to match a single line...
#-            del self.regexes[self.whichmatched]
#+            tmp_regexes = self.regexes
#+            self.regexes = []
#+            which = 0
#+            for regex in tmp_regexes:
#+                matchobj = re.search(regex, oneresult)
#+                if not matchobj:
#+                    self.regexes.append(regex)
if __name__ == "__main__":

    def logmessage(msg):
        'Log a message to our system log'
        os.system('logger "LOGWATCHER TEST: %s"' % msg)

    def testlog(logfilename):
        'Function for doing basic testing of LogWatcher module'
        watcher = LogWatcher(logfilename, ['(Test message 1)', '(Test message 2)']
        ,   debug=0, returnonlymatch=True, timeout=2)
        watcher.setwatch()
        logmessage('Test message 2')
        result = watcher.look()
        assert(result == 'Test message 2')

        watcher.setwatch()
        logmessage('Test message 1')
        result = watcher.look()
        assert(result == 'Test message 1')

        watcher.setwatch()
        logmessage('Test message 2')
        logmessage('Test message 1')
        results = watcher.lookforall()
        assert results == ['Test message 2', 'Test message 1']

        # Test the no-match case
        watcher.setwatch()
        result = watcher.look()
        assert result is None

        print 'No asserts: Test succeded! WOOT!!'

    if os.access('/var/log/syslog', os.R_OK):
        testlog('/var/log/syslog')
    elif os.access('/var/log/messages', os.R_OK):
        testlog('/var/log/messages')
