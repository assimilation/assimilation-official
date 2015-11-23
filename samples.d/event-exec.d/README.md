Here is a collection of sample scripts which do various things when interesting events are observed.

To use any of these scripts, make it executable place it in /usr/share/assimilation/notification.d.

Most of these scripts need some kind of configuation or customization for your particular purpose. For more details, read the script.

Each script runs one at a time, and they run in _ls_ sort order. Conventionally this would mean you give the file names a four-digit prefix. If you wanted the email notification script to run first, you might name it /usr/share/assimilation/notification.d/0001-sendemail.sh
emailnotification.sh

Each of these scripts is invoked with two arguments:
 - **event type** currently one of (_create, up, down, warn, unwarn, update, delete_)
 - **graph node type** - currently one of (_Drone, IPaddrNode, MonitorAction, NICNode, ProcessNode, SystemNode_)

The key to handling these events is to know what the interesting attributes of each kind of event are
There are two kinds of attributes that show up in the environment.
 - scalar attributes from the database node associated with the event
 - scalar attributes from the an "extrainfo" provided for this particular event

If you want to process the JSON, it is provided as standard input to event scripts. The event itself has two interesting attributes
 - _associatedobject_ - the object to which this event has occurred
 - _extrainfo_ - extra information associated with this particular event - May be _null_.
