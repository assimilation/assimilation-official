#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number fileencoding=utf-8
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
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
"""
This module implements classes associated with Events in the Assimilation Project.
"""


class AssimEvent(object):
    """This class is all about highlighting events which others might want to know about.
    Other objects can register to be notified about the creation of new events.
    Or at least they will be able to when that code is written ;-).
    All of this happens without any concern by the event objects themselves.
    It is handled by static methods and a tiny bit of code in our constructor.
    """

    # Legal event types
    CREATEOBJ = 0  # Object was newly created
    OBJUP = 1  # Object status is now up
    OBJDOWN = 2  # Object status is now down
    OBJWARN = 3  # Object status is now in a warning state
    OBJUNWARN = 4  # Object status has exited a warning state
    OBJUPDATE = 5  # Object was updated
    OBJDELETE = 6  # Object is about to be deleted

    eventtypenames = {
        CREATEOBJ: "create",
        OBJUP: "up",
        OBJDOWN: "down",
        OBJWARN: "warn",
        OBJUNWARN: "unwarn",
        OBJUPDATE: "update",
        OBJDELETE: "delete",
    }

    event_observation_enabled = True

    observers = []

    def __init__(self, associatedobject, eventtype, extrainfo=None):
        """Initializer for AssimEvent class.
        We save our parameters then notify our registered observers.

        Parameters:
        ----------
        associatedobject: GraphNode
            The GraphNode associated with this event
        eventtype: int
            one of AssimEvent.CREATEOBJ, AssimEvent.OBJUP, AssimEvent.OBJDOWN,
            AssimEvent.OBJWARN, AssimEvent.OBJUPDATE or AssimEvent.OBJDELETE
        """
        if eventtype not in AssimEvent.eventtypenames:
            raise ValueError("Event type [%s] is not a legal event type" % eventtype)

        self.associatedobject = associatedobject
        self.eventtype = eventtype
        self.extrainfo = extrainfo
        if AssimEvent.event_observation_enabled:
            self.notifynewevent()

    @staticmethod
    def disable_all_observers():
        """Useful when testing and we don't want to trigger external event observers..."""
        AssimEvent.event_observation_enabled = False

    @staticmethod
    def enable_all_observers():
        """Useful when testing and we want to undo the operation above..."""
        AssimEvent.event_observation_enabled = True

    @staticmethod
    def is_registered(observer):
        """Return True if the given observer is registered with us.
        """
        return observer in AssimEvent.observers

    @staticmethod
    def registerobserver(observer):
        """Static method for registering an observer with the AssimEvent class.
        The given observer object must implement a 'notifynewevent' method
        -- because we will surely call it :-D.
        """
        if not hasattr(observer, "notifynewevent"):
            raise AttributeError("observer must have a notifynewevent method")
        if observer not in AssimEvent.observers:
            AssimEvent.observers.append(observer)

    @staticmethod
    def unregisterobserver(observer):
        """Static method for unregistering an observer with the AssimEvent class.
        We return True if the given observer was registered with us, False otherwise.
        """
        for j in range(0, len(AssimEvent.observers)):
            if AssimEvent.observers[j] is observer:
                del AssimEvent.observers[j]
                return True
        return False

    def notifynewevent(self):
        """method for notifying all our observers that a new event
        has been created.
        We call the 'notifynewevent' method in each registered observer object.
        """
        for observer in AssimEvent.observers:
            observer.notifynewevent(self)
