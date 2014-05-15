/**
 * gtest02.c - miscellaneous client-only tests not requiring mainloop.
 * These tests test things which are only used by the nanoprobes, so there are no python
 * wrappers for them.
 *
 * This file is part of the Assimilation Project.
 *
 * @author  Alan Robertson <alanr@unix.sh> - Copyright &copy; 2013 - Assimilation Systems Limited
 * @n
 *  The Assimilation software is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  The Assimilation software is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
 */

#include <projectcommon.h>
#ifdef HAVE_MCHECK_H
#	include <mcheck.h>
#endif
#include <string.h>
#include <resourcecmd.h>
#include <resourcequeue.h>
#include <childprocess.h>
#include <stdio.h>
#include <string.h>
#include <malloc.h>

FSTATIC void	test_all_freed(void);
FSTATIC gboolean logfatal_function(const gchar*, GLogLevelFlags, const gchar*,gpointer);
FSTATIC void	set_expected_failures(const char** the_usual_suspects);
FSTATIC void	test_invalid_resourcecmd(void);
FSTATIC void	test_invalid_queuecmd(void);
FSTATIC void	test_childprocess_failure(void);

char *		bad_msg = NULL;
const char **	expected_msgs = NULL;

FSTATIC void
set_expected_failures(const char** the_usual_suspects)
{
	g_log_set_fatal_mask(G_LOG_DOMAIN, 0);
	g_test_log_set_fatal_handler (logfatal_function, the_usual_suspects);
	expected_msgs = the_usual_suspects;
}

FSTATIC void
test_all_freed(void)
{
	int	live_obj_count = proj_class_live_object_count();
	const char **	mptr;

	if (live_obj_count > 0) {
		proj_class_dump_live_objects();
		g_assert_cmpint(live_obj_count, ==, 0);
	}
	if (bad_msg) {
		g_message("Message [\"%s\"] not found in expected messages for this test."
		,	bad_msg);
		fflush(stdout);
		for (mptr = expected_msgs; mptr && *mptr; ++mptr) {
			g_message("Expected message: \"%s\"", *mptr);
			fflush(stdout);
		}
		g_assert(bad_msg == NULL);
		free(bad_msg);
		bad_msg = NULL;
	}
}

FSTATIC gboolean
logfatal_function(
	const gchar *	log_domain
,	GLogLevelFlags	log_level
,	const gchar *	message
,	gpointer	user_data)
{
	const char **	messagelist = (const char **)user_data;

	const char **	mptr;
	int		msgcount = 0;

	(void)log_domain;
	(void)log_level;

	if (log_level >= G_LOG_LEVEL_MESSAGE) {
		return FALSE;
	} 
	// Old versions of glib don't seem to handle user_data...
	if (messagelist == NULL) {
		messagelist = expected_msgs;
	}
	for (mptr = messagelist; mptr && *mptr; ++mptr) {
		++ msgcount;
		if (strstr(message, *mptr) != NULL) {
			return FALSE;
		}
	}
	g_message("Message [\"%s\"] not found in %d expected messages."
	,	message, msgcount);
	fflush(stdout);
	for (mptr = messagelist; mptr && *mptr; ++mptr) {
		g_message("Expected message: \"%s\"", *mptr);
		fflush(stdout);
	}
	g_message("ABORTING: message was not an expected failure.");
	fflush(stdout);
	g_message("No further gtest02 tests will be run.  Bye bye!");
	fflush(stdout);
	if (!bad_msg) {
		bad_msg = strdup(message);
		expected_msgs = messagelist;
	}
	return FALSE;
}

///< Try various invalid resource command initializers
#define	DUMB	"\""CONFIGNAME_INSTANCE"\":\"dumb\""
#define	PROV	",\"" REQPROVIDERNAMEFIELD "\": \"heartbeat\"}"



FSTATIC void
test_childprocess_failure(void)
{
	ChildProcess*	my_child_is_a_failure;
	char 	devnull [] = "/dev/null";
	char* 	argv[] = {devnull, NULL};
	const char *	expected_failures[] = {"Failed to execute child process \"/dev/null\"", NULL};

	set_expected_failures(expected_failures);

	my_child_is_a_failure = childprocess_new(0
	,	argv		// command and arguments
	,	NULL		// envp
	,	NULL		// envmod
	,	"/"		// curdir
	,	NULL		// notify process
	,	FALSE		// save_stdout
	,	"foo"		// logdomain
	,	"bar"		// logprefix
	,	0		// GLogLevelFlags loglevel
	,	0		// timeout seconds
	,	NULL		// user_data
	,	CHILD_LOGALL	// ChildErrLogMode logmode
	,	"failurechild"	// logname
	);
	g_assert(my_child_is_a_failure == NULL);
	test_all_freed();
}

FSTATIC void
test_invalid_resourcecmd(void)
{

	const char *	json_cmds[] = {
		"{}",

		"{\"" REQCLASSNAMEFIELD "\": \"NOSUCHRESOURCECLASS\","DUMB PROV,

		"{\"" REQCLASSNAMEFIELD "\":\"ocf\"" PROV,

		"{\"" REQCLASSNAMEFIELD "\":\"ocf\"," DUMB PROV,

		"{\"" REQCLASSNAMEFIELD "\":\"ocf\", \"" CONFIGNAME_TYPE "\":\"NOSUCHOCFRESOURCETYPE\","DUMB PROV,

		"{\"" REQCLASSNAMEFIELD "\":\"ocf\", \"" CONFIGNAME_TYPE "\":\"NOSUCHOCFRESOURCETYPE\",\""
				REQOPERATIONNAMEFIELD"\":\"monitor\","DUMB PROV,

		"{\"" REQCLASSNAMEFIELD "\":\"ocf\", \"" CONFIGNAME_TYPE "\":\"NOSUCHOCFRESOURCETYPE\",\""
				REQOPERATIONNAMEFIELD"\":\"monitor\","
				"\""REQENVIRONNAMEFIELD"\":\"notahash\","DUMB PROV,

		"{\"" REQCLASSNAMEFIELD "\":\"lsb\", \"" CONFIGNAME_TYPE "\":\"NOSUCHOCFRESOURCETYPE\",\""
				REQOPERATIONNAMEFIELD"\":\"monitor\"}",
		NULL
	};
	const char *	expected_failures[] = {
		": No class name in request [{}]",
		": No resource name in request [{\"class\":\"ocf\",\"provider\":\"heartbeat\"}]",
		": Invalid resource class [NOSUCHRESOURCECLASS]",
		": NULL resourcecmd request",
		": No type field in OCF agent request.",
		": No operation field in OCF agent request.",
		": No OCF Resource agent [/usr/lib/ocf/resource.d/heartbeat/NOSUCHOCFRESOURCETYPE]",
		": No LSB Resource agent [/etc/init.d/NOSUCHOCFRESOURCETYPE]",
		": environ field in OCF request is invalid.",
		NULL
	};
	guint		j;

	set_expected_failures(expected_failures);

	for (j=0; j < DIMOF(json_cmds); ++j) {
		ConfigContext*	request = NULL;
		ResourceCmd*	rcmd;
		if (json_cmds[j] != NULL) {
			request = configcontext_new_JSON_string(json_cmds[j]);
			g_assert(request != NULL);
		}
		rcmd = resourcecmd_new(request, NULL, NULL);
		g_assert(NULL == rcmd);
		if (NULL != rcmd) {
			UNREF(rcmd);
		}
		if (NULL != request) {
			UNREF(request);
		}
	}
	test_all_freed();
}

FSTATIC void
test_invalid_queuecmd(void)
{
	ResourceQueue*	rq = resourcequeue_new(0);
	const char *	json_cmds[] = {
		"{\"" REQCLASSNAMEFIELD "\":\"ocf\", \"" CONFIGNAME_TYPE "\":\"Dummy\","
				"\""REQENVIRONNAMEFIELD"\":{},"
				"\""REQOPERATIONNAMEFIELD"\":\"monitor\","DUMB PROV,
	};
	unsigned	j;
	const char *	expected_failures[] = {
		": Request rejected - no request id",
		": NULL resourcecmd request",
		NULL,
	};

	set_expected_failures(expected_failures);
	
	
	g_assert_cmpint(rq->Qcmd(rq, NULL, NULL, NULL), ==, 0);


	for (j=0; j < DIMOF(json_cmds); ++j) {
		ConfigContext*	cfg = configcontext_new_JSON_string(json_cmds[j]);
		g_assert_cmpint(rq->Qcmd(rq, cfg, NULL, NULL), ==, 0);
		UNREF(cfg);
	}
	UNREF(rq);
	test_all_freed();
}


/// Test main program ('/gtest02') using the glib test fixtures
int
main(int argc, char ** argv)
{
#ifdef HAVE_MCHECK_PEDANTIC
	g_assert(mcheck_pedantic(NULL) == 0);
#else
#	ifdef HAVE_MCHECK
	g_assert(mcheck(NULL) == 0);
#	endif
#endif
	g_setenv("G_MESSAGES_DEBUG", "all", TRUE);
	g_log_set_fatal_mask(NULL, 0);	// I know G_LOG_LEVEL_ERROR is fatal anyway...
	g_test_init(&argc, &argv, NULL);
	g_log_set_fatal_mask(NULL, 0);
	g_test_add_func("/gtest02/test_childprocess_failure", test_childprocess_failure);
	g_test_add_func("/gtest02/test_invalid_resourcecmd", test_invalid_resourcecmd);
	g_test_add_func("/gtest02/test_invalid_queuecmd", test_invalid_queuecmd);
	return g_test_run();
}
