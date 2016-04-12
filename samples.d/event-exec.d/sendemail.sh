#!/bin/sh -eu
#
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# sendemail.sh: Sends emails when various kinds of events occur
#
# This is a sample script. You *will* have to change it to suit your purpose.
#
# It's purpose is to illustrate how one the Assimilation event API works.
#
# It is a more polished version of a script written during the 2015 OSMC Hackathon in Nuremberg.de
#
# This file is part of the Assimilation Project and is available under alternative licenses.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2015 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
# Paid support is available from Assimilation Systems Limited
#   - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.
# If not, see http://www.gnu.org/licenses/
#
#
#   Set the destination email addresses here...
#
EMAILDESTS="root@example.org"
RETURNADDR="AssimilationCMDB@example.org"
#
# Select the default mail method here...
# The choices below are 'mail_email', 'mailx_email', and 'mutt_email'
# Feel free to add your favorite ;-).
#
EMAIL_METHOD=mail_email
JSONMIMETYPE='application/json'
# Attributes to omit from our message body
EGREP_V_FILTER='^(ASSIM_JSONobj|_.*|ASSIM_JSON__hash__.*)='

trap 'cd /; rm -fr $TMPDIR' 0
TMPDIR=$(mktemp -d)

# Copy the JSON from this event into an appropriately named tmp file
# The name needs to end in .json or .JSON, so that the mail methods that infer
# mimetype from the suffix will get a reasonable answer.
#
# The event API passes pass the full event JSON through stdin - to avoid potential limits
# on the total size of the environment, or a single environment variable.
#
create_json_attachment() {
    prefix=$1
    shift
    for arg
    do
        prefix="${prefix}_${1}"
        shift
    done
    JSONFILE=$TMPDIR/assimilation.$prefix.json
    cat > $JSONFILE
}

# Send our email using mailx - first argument is the subject, the rest are destinations
# Message body comes from stdin.
mailx_email() {
    subject=$1
    shift
    mailx -a "$JSONFILE" -r "$RETRUNADDR" -s "$subject" "$@"
}

# Send our email using GNU mailutils email command (and perhaps some others)
# The first argument is subject, the rest are destinations
# Message body comes from stdin.
mail_email() {
    subject=$1
    shift
    mail "--content-type=$JSONMIMETYPE" -A "$JSONFILE" \
        --return-address "$RETURNADDR" -s "$subject" "$@"
}

# Send our email using mutt - first argument is subject, remaining are destinations
# Message body comes from stdin.
mutt_email() {
    subject=$1
    shift
    mutt "$subject" -a "$JSONFILE" -- "$@"
}

#
#   Construct an email body with interesting information about our event
#   This includes the values of all the ASSIM_ environment variables
#
email_body() {
    envout=$TMPDIR/env.txt
    env > ${envout}
    envnames=$TMPDIR/envnames.txt
    grep '^ASSIM_' < ${envout} | egrep -v "${EGREP_V_FILTER}" | sed -e 's%=.*%%' > ${envnames}
    sort $envnames -o $envnames
    set -- $MASTER_ARGLIST
    cat <<-!EMAIL
		Reason for email: Observed "$1" Event for $2

		Full event information is in the attached JSON file.

		Below are key details of this event.

		!EMAIL
    for envvar in $(cat $envnames)
    do
        grep "^${envvar}=" < ${envout}
    done | sed -e 's%^ASSIM_%%'
}

# Send our email using selected method: first arg is the subject, rest are destinations
# The default set of destinations come from ${EMAILDESTS} at the beginning of this file.
# Message body is created from our event details.
sendemail() {
    email_body | $EMAIL_METHOD "$@" ${EMAILDESTS}
}

#
# Send notification of a service going up or down
#
notify_service() {
    status=$1

    case ${status} in
        down)   sendemail "WARNING: Service down: $ASSIM_monitorname";;
        up)     sendemail "HURRAY: Service up: $ASSIM_monitorname";;
    esac
}

#
# Send notification of a system (Drone) going up or down
#
notify_system() {
    status=$1

    case ${status} in
        up)      sendemail "HURRAY: System $ASSIM_designation is back up";;
        down)
            case $ASSIM_reason in
                HBSHUTDOWN)
                    sendemail "WARNING: System $ASSIM_designation was gracefully shut down";;
                *)
                    sendemail "WARNING: System $ASSIM_designation is down [$ASSIM_reason]";;
            esac
    esac
}

#
# Send notification of a system (Drone) going in or out of compliance with best practices
# We only send notifications on transitions from in->out or out->in
#
notify_warn_unwarn() {
    eventtype=$1
    SYSTEM=$ASSIM_designation
    CAT=$ASSIM_category
    RULE=$ASSIM_ruleid
    case $eventtype in
        warn)
            sendemail "WARNING: System $SYSTEM out of compliance with $CAT best practice $RULE"
            ;;
        unwarn)
            sendemail "HURRAY: System $SYSTEM now in compliance with $CAT best practice $RULE"
            ;;
    esac
}

# Every object in our database has an object type - $ASSIM_nodetype
# This is also passed to our 'main' as $2
process_objstatus() {
    case $ASSIM_nodetype in
        Drone)          notify_system  "$@";;
        MonitorAction)  notify_service "$@";;
    esac
}

# Dump out the information we have on the event
dump_event() {
    echo "$(date): GOT EVENT $*"
    email_body
    echo "====== JSON from $JSONFILE ========"
    cat $JSONFILE
    printf '\n=============================================\n'
}

#
# We are invoked with two arguments:
#   $1: event type
#       create, up, down, warn, unwarn, update, delete
#   $2: type of associated database node
#       Currently could be one of:
#           Drone, IPaddrNode, MonitorAction, NICNode, ProcessNode, SystemNode

#
#   This script only processes up and down events, and those currently apply only to
#       Drone and MonitorAction nodes

MASTER_ARGLIST="$*"
create_json_attachment "$@"
#dump_event "$@"
case $1 in
    up|down)        process_objstatus  "$@";;
    warn|unwarn)    notify_warn_unwarn "$@";;
    #*)          dump_event "$@";;
esac
