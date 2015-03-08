#!/bin/sh
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# Program to regression test discovery agents.
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2015 - Assimilation Systems Limited
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
ourdir=$(dirname $0)
TESTDIR=../../discovery_agents
INPUTDIR=$PWD/$ourdir/discovery_input
OUTPUTDIR=$PWD/$ourdir/discovery_output
TMPOUT=/tmp/$$.testout


we_have_cmd() {
    cmd=$1
    for dir in $(echo "$PATH" | tr ':' ' ')
    do
        if
            [ -f $dir/$cmd -a -x $dir/$cmd ]
        then
            return 0
        fi
    done
    return 1
}

run_regression_test() {
    test=$1
    varname=$2
    TESTNAME=$TESTDIR/$test
    TESTFILE=$INPUTDIR/$test
    OUTFILE=$OUTPUTDIR/$test
    cd $INPUTDIR
    if
        eval export $varname='$test'
        $TESTNAME > $TMPOUT 2>&1
    then
        : OK it thinks it succeeded
        if
            jsonlint $TMPOUT >/dev/null
        then
            : OK
        else
            jsonlint -v $TMPOUT
            echo "Discovery $test produced invalid JSON - output follows"
            cat $OUTFILE
            return 1
        fi
        if
            [ ! -f $OUTFILE ]
        then
            echo "No previous output for agent $test"
            cp $TMPOUT $OUTFILE
            return 0
        fi
        if
            cmp $TMPOUT $OUTFILE
        then
          : Great!
        else
            echo "ERROR: Discovery output $test was incorrect."
            echo "Diff -u follows"
            diff -u $OUTFILE $TMPOUT
            return 1
        fi
    else
        rc=$?
        echo "ERROR: Discovery test $test failed - output follows."
        cat $TMPOUT
        echo "END OF TEST $test FAILURE OUTPUT"
        return 1
    fi
    if
        eval export $varname='/tmp/foo/bar/no-such-file'
        $TESTNAME > $TMPOUT 2>&1
    then
        if
            jsonlint $TMPOUT >/dev/null
        then
            if
                we_have_cmd 'jq'
            then
                ERROUT=$(jq --ascii-output --raw-output .data.NODATA < $TMPOUT)
                case $ERROUT in
                    *ERROR*)    : OK;;
                    *)  echo "Discovery failure test produced incorrect result [$ERROUT]"
                        return 1;;
                esac
            fi
        else
            jsonlint -v $TMPOUT
            echo "Discovery failure $test produced invalid JSON - output follows"
            cat $OUTFILE
            return 1
        fi
    else
        echo "ERROR: Discovery failure $test exited with return code $?"
        return 1
    fi
    echo "Discovery test $test succeeded."
    return 0
}

failcount=0
testlines='mdadm MDADM_CONFIG
nsswitch NSSWITCH_CONFIG
pam PAM_DIRECTORY
partitions PROC_PARTITIONS
sshd SSHD_CONFIG'
echo "$testlines" |
while
  read testname envname
do
    run_regression_test "$testname" "$envname"
    failcount=$(expr $failcount + $?)
done
exit $failcount
