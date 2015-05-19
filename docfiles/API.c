/**
@page APIs APIs
At this point in time, we support three different APIs:
- a command line query API
- a REST query API
- and event API

@section CLI_API Command Line Query API
The command line query provides the ability to perform a number of canned queries
from the command line, and receive the results to standard output.
There is a <a href="http://assimilationsystems.com/2014/04/02/new-command-line-queries-in-the-assimilation-software/">blog article</a>  describing the API in more detail.
This API is suitable for using via scripts or integrating into chat room bots.

@section REST_API REST Query API
The REST query API is an exact mirror of the command line queries, except they are provided over
a REST interface.
At this writing, the REST server (currently named flask/hello.py) is not started by default.

@section event_API Event API
The event API is a simple fork/exec API.
When an event occurs in the CMA, it creates an AssimEvent object for that event.
The information from that AssimEvent object is then passed to whatever scripts are executable
in /usr/share/notification.d.
Simple attributes of the AssimEvent come through named ASSIM_<i>attribute-name</i>.
More specifically, string, unicode, into, float, long and bool objects receive this treatment.
The entire AssimEvent is rendered into a JSON string and passed to the script as the
environment variable ASSIM_JSONobj.

In the future, events may be available by other methods besides fork/exec, but not
as of this writing.
*/
