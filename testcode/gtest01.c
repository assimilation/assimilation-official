/**
 * gtest01.c - miscellaneous glib mainloop-based tests.
 * Most of these tests involve the glib mainloop - which is harder to test in python.
 * Otherwise we prefer to test in python because it exercises both the C code and the python wrappers for it
 * and for the most part, they're easier to write.
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
#ifdef HAVE_UNISTD_H
#	include <unistd.h>
#endif
#include <sys/types.h>
#include <signal.h>
#include <string.h>
#include <glib.h>
#include <gmainfd.h>
#include <logsourcefd.h>
#include <configcontext.h>
#include <childprocess.h>
#include <resourcecmd.h>
#include <resourcelsb.h>
#include <resourcequeue.h>

GMainLoop*	mainloop;
FSTATIC void	test_read_command_output_at_EOF(void);
FSTATIC void	test_log_command_output(void);
FSTATIC void	test_save_command_output(void);
FSTATIC void	test_childprocess_log_all(void);
FSTATIC void	test_childprocess_false(void);
FSTATIC void	test_childprocess_timeout(void);
FSTATIC void	test_childprocess_save_command_output(void);
FSTATIC void	quit_at_child_exit(GPid pid, gint status, gpointer gmainfd);
FSTATIC void	check_output_at_exit(GPid pid, gint status, gpointer gmainfd);
FSTATIC void	quit_at_childprocess_exit(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped);
FSTATIC void	generic_childprocess_test(gchar** argv, ConfigContext*, gboolean save_stdout, char * curdir, int timeout);
FSTATIC void	test_childprocess_save_command_output_timeout(void);
FSTATIC void	test_childprocess_save_command_output_signal(void);
FSTATIC void	test_childprocess_stderr_logging(void);
FSTATIC void	test_childprocess_modenv(void);
FSTATIC void	test_safe_ocfops(void);
FSTATIC void	test_safe_queue_lsbops(void);
FSTATIC void	test_safe_queue_ocfops(void);
FSTATIC void	expect_ocf_callback(ConfigContext* request, gpointer user_data, enum HowDied reason
,		int rc, int signal, gboolean coredump, const char * stringresult);
FSTATIC void	test_all_freed(void);

#define	HELLOSTRING	": Hello, world."
#define	HELLOSTRING_NL	(HELLOSTRING "\n")

enum HowDied	test_expected_death = EXITED_ZERO;
int		test_expected_exitcode = 0;
int		test_expected_signal = 0;
int		test_expected_linecount = 1;
int		test_expected_charcount = 0;
int		test_expected_stderr_linecount = 0;
int		test_expected_stderr_charcount = 0;
const char *	test_expected_string_return = NULL;
gboolean	no_dummy_RA = FALSE;

void
test_all_freed(void)
{
	int	live_obj_count = proj_class_live_object_count();

	if (live_obj_count > 0) {
		proj_class_dump_live_objects();
		g_assert_cmpint(live_obj_count, ==, 0);
	}
}

/// Make sure we read our HELLOSTRING when the process exits
FSTATIC void
check_output_at_exit(GPid pid, gint status, gpointer gmainfd)
{
	GMainFd*	cmdout = CASTTOCLASS(GMainFd, gmainfd);
	(void)pid;
	g_assert_cmpint(status, ==, 0);
	g_assert(cmdout->textread != NULL);
	g_assert_cmpint(strnlen(cmdout->textread->str, cmdout->textread->len), ==, cmdout->textread->len);
	g_assert_cmpstr(cmdout->textread->str, ==, HELLOSTRING "\n");
	//g_print("GOT [%s]\n", cmdout->textread->str);
	g_main_loop_quit(mainloop);
}

/// Test to run a command and verify that we can capture its output in a string in the gmainloop environment
FSTATIC void
test_read_command_output_at_EOF(void)
{
	GPid		childpid;
	gint		stdoutfd;
	GError*		failcode = NULL;
	GMainFd*	cmdout;
	gchar		echo[] = "/bin/echo";
	gchar		hello[] = HELLOSTRING;
	gchar* 	argv[] = {echo, hello, NULL};		// Broken glib API...
	gint	cmdid;
	mainloop = g_main_loop_new(g_main_context_default(), TRUE);
	g_spawn_async_with_pipes(
		NULL,				// Current directory
		argv,				// Arguments
		NULL,				// environment
		G_SPAWN_DO_NOT_REAP_CHILD,	// GSpawnFlags flags,
		NULL,				// GSpawnChildSetupFunc child_setup,
		NULL,				// gpointer user_data,
		&childpid,			// GPid *child_pid,
		NULL,				// gint *standard_input,
		&stdoutfd,			// gint *standard_output,
		NULL,				// gint *standard_error,
		&failcode);			// GError **error
	
	cmdout = gmainfd_new(0, stdoutfd, G_PRIORITY_HIGH, g_main_context_default());
	//g_print("Spawned child %d with fd %d\n", childpid, stdoutfd);
	g_assert_cmpint(childpid, >, 0);
	g_assert_cmpint(stdoutfd, >, 0);
	cmdid = g_child_watch_add(childpid, check_output_at_exit, cmdout);
	g_assert_cmpint(cmdid, >, 0);
	g_main_loop_run(mainloop);
	g_source_unref(&cmdout->baseclass);
	g_main_loop_unref(mainloop);
	mainloop=NULL;
	if (proj_class_live_object_count() != 0) {
		proj_class_dump_live_objects();
	}
	g_assert_cmpint(proj_class_live_object_count(), ==, 0);
}

/// Quit when the child exits - look for HELLOSTRING characters being logged.
FSTATIC void
quit_at_child_exit(GPid pid, gint status, gpointer logsourcefd)
{
	LogSourceFd*	logsrc = CASTTOCLASS(LogSourceFd, logsourcefd);
	
	(void)pid;
	g_assert_cmpint(status, ==, 0);
	g_assert_cmpint(logsrc->linecount, ==, 1);
	// sizeof(HELLOSTRING) includes a NULL.  echo effectively replaces the NULL with a '\n'
	g_assert_cmpint(logsrc->charcount, ==, sizeof(HELLOSTRING));
	g_main_loop_quit(mainloop);
}

// We logged the output of echo HELLOSTRING to standard output - let's see if it worked...
FSTATIC void
quit_at_childprocess_exit(ChildProcess*self, enum HowDied notice, int rc, int signal, gboolean core_dumped)
{
	LogSourceFd*	stdoutfd;
	(void)core_dumped;

	g_assert_cmpint(notice, ==, test_expected_death);
	if (notice == EXITED_ZERO || notice == EXITED_NONZERO) {
		g_assert_cmpint(rc, ==, test_expected_exitcode);
	}
	if (notice == EXITED_SIGNAL) {
		g_assert_cmpint(signal, ==, test_expected_signal);
	}
	if (test_expected_string_return == NULL) {
		g_assert_cmpint(OBJ_IS_A(self->stdout_src, "LogSourceFd"), ==,  TRUE);
		stdoutfd = CASTTOCLASS(LogSourceFd, self->stdout_src);
		g_assert_cmpint(stdoutfd->charcount, ==, test_expected_charcount);
		g_assert_cmpint(stdoutfd->linecount, ==, test_expected_linecount);
	}else{
		g_assert(self->stdout_src->textread != NULL);
		if (self->stdout_src->textread != NULL) {
			g_assert(self->stdout_src->textread->str != NULL);
			g_assert_cmpstr(self->stdout_src->textread->str, ==, test_expected_string_return);
		}
	}
	g_assert_cmpint(self->stderr_src->charcount, ==, test_expected_stderr_charcount);
	g_assert_cmpint(self->stderr_src->linecount, ==, test_expected_stderr_linecount);

	g_main_loop_quit(mainloop);
}

/// A test for just testing our ability to log things we read from a pipe.
FSTATIC void
test_log_command_output(void)
{
	GPid		childpid;
	gint		stdoutfd;
	GError*		failcode = NULL;
	LogSourceFd*	cmdlog;
	gchar		echo[] = "/bin/echo";
	gchar		hello[] = HELLOSTRING;
	gchar* 	argv[] = {echo, hello, NULL};		// Broken glib API...
	gint	cmdid;
	//proj_class_incr_debug(NULL);
	//proj_class_incr_debug(NULL);
	//proj_class_incr_debug(NULL);
	mainloop = g_main_loop_new(g_main_context_default(), TRUE);
	g_spawn_async_with_pipes(
		NULL,				// Current directory
		argv,				// Arguments
		NULL,				// environment
		G_SPAWN_DO_NOT_REAP_CHILD,	// GSpawnFlags flags,
		NULL,				// GSpawnChildSetupFunc child_setup,
		NULL,				// gpointer user_data,
		&childpid,			// GPid *child_pid,
		NULL,				// gint *standard_input,
		&stdoutfd,			// gint *standard_output,
		NULL,				// gint *standard_error,
		&failcode);			// GError **error
	
	cmdlog = logsourcefd_new(0, stdoutfd, G_PRIORITY_HIGH, g_main_context_default()
	,			 G_LOG_DOMAIN, G_LOG_LEVEL_MESSAGE, __FUNCTION__);
	//g_print("Spawned child %d with fd %d\n", childpid, stdoutfd);
	g_assert_cmpint(childpid, >, 0);
	g_assert_cmpint(stdoutfd, >, 0);
	cmdid = g_child_watch_add(childpid, quit_at_child_exit, cmdlog);
	g_assert_cmpint(cmdid, >, 0);
	g_main_loop_run(mainloop);
	g_source_unref(&cmdlog->baseclass.baseclass);
	g_main_loop_unref(mainloop);
	mainloop=NULL;
	if (proj_class_live_object_count() != 0) {
		proj_class_dump_live_objects();
	}
	g_assert_cmpint(proj_class_live_object_count(), ==, 0);
}

/// A generic helper function for testing things about childprocess_new()
FSTATIC void
generic_childprocess_test(gchar** argv, ConfigContext* envmod, gboolean save_stdout, char * curdir, int timeout)
{
	ChildProcess*	child;

	mainloop = g_main_loop_new(g_main_context_default(), TRUE);
	child = childprocess_new(0	// object size (0 == default size)
,		argv			// char** argv
,		NULL			// char** envp
,		envmod			// ConfigContext*envmod
,		curdir			// const char* curdir
,		quit_at_childprocess_exit
		//gboolean	(*notify)(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped)
,		save_stdout		//	gboolean save_stdout
,		G_LOG_DOMAIN		// const char * logdomain
,		__FUNCTION__		// const char * logprefix
,		G_LOG_LEVEL_MESSAGE	//	GLogLevelFlags loglevel
,		timeout			//guint32 timeout_seconds);
,		NULL			// gpointer user_data
,		CHILD_NOLOG		// exit logging mode
,		NULL			// logging name - defaults to argv[0]
	);
	g_main_loop_run(mainloop);
	UNREF(child);
	g_main_loop_unref(mainloop);
	mainloop=NULL;
	if (envmod) {
		UNREF(envmod);
	}
	if (proj_class_live_object_count() != 0) {
		proj_class_dump_live_objects();
	}
	g_assert_cmpint(proj_class_live_object_count(), ==, 0);
}

/// This test produces output which is logged.  We verify the character and line counts.
FSTATIC void
test_childprocess_log_all(void)
{
	gchar		echo[] = "/bin/echo";
	gchar		hello[] = HELLOSTRING;
	gchar* 	argv[] = {echo, hello, NULL};		// Broken glib API...

	test_expected_death = EXITED_ZERO;
	test_expected_exitcode = 0;
	test_expected_signal = 0;
	test_expected_linecount = 1;
	test_expected_charcount = sizeof(hello);
	test_expected_stderr_linecount = 0;
	test_expected_stderr_charcount = 0;
	test_expected_string_return = NULL;
	generic_childprocess_test(argv, NULL, FALSE, NULL, 0);
}

/// This test exits with return code 1 (the false command)
FSTATIC void
test_childprocess_false(void)
{
	gchar		false[] = "/bin/false";
	gchar* 	argv[] = {false, NULL};		// Broken glib API...

	test_expected_death = EXITED_NONZERO;
	test_expected_exitcode = 1;
	test_expected_signal = 0;
	test_expected_linecount = 0;
	test_expected_charcount = 0;
	test_expected_stderr_linecount = 0;
	test_expected_stderr_charcount = 0;
	test_expected_string_return = NULL;
	generic_childprocess_test(argv, NULL, FALSE, NULL, 0);
}

/// This test outputs a string which is then saved.
FSTATIC void
test_childprocess_save_command_output(void)
{
	gchar		echo[] = "/bin/echo";
	gchar		hello[] = HELLOSTRING;
	gchar* 	argv[] = {echo, hello, NULL};		// Broken glib API...

	test_expected_death = EXITED_ZERO;
	test_expected_exitcode = 0;
	test_expected_signal = 0;
	test_expected_linecount = 0;
	test_expected_charcount = 0;
	test_expected_stderr_linecount = 0;
	test_expected_stderr_charcount = 0;
	test_expected_string_return = HELLOSTRING_NL;
	generic_childprocess_test(argv, NULL, TRUE, NULL, 0);
}
FSTATIC void
test_childprocess_modenv(void)
{
	gchar		shell[] = "/bin/sh";
	gchar		dashc[] = "-c";
	gchar		echocmd[] = "echo $TRITE $HOME";
	gchar* 	argv[] = {shell, dashc, echocmd, NULL};		// Broken glib API...
	NetAddr*	home = netaddr_string_new("127.0.0.1");
	ConfigContext*	envmod = configcontext_new_JSON_string("{\"TRITE\":\"There's no place like\"}");

	envmod->setaddr(envmod, "HOME", home);
	UNREF(home);
	test_expected_death = EXITED_ZERO;
	test_expected_exitcode = 0;
	test_expected_signal = 0;
	test_expected_linecount = 0;
	test_expected_charcount = 0;
	test_expected_stderr_linecount = 0;
	test_expected_stderr_charcount = 0;
	test_expected_string_return = "There's no place like 127.0.0.1\n";
	generic_childprocess_test(argv, envmod, TRUE, NULL, 0);
}

/// We produce some output, then exceed our timeout with a sleep.
/// The output is set up to be captured.
FSTATIC void
test_childprocess_save_command_output_timeout(void)
{
	gchar		shell[] = "/bin/sh";
	gchar		dashc[] = "-c";
	gchar		hello[] = "echo \""HELLOSTRING"\"; sleep 100";
	gchar* 	argv[] = {shell, dashc, hello, NULL};		// Broken glib API...

	test_expected_death = EXITED_TIMEOUT;
	test_expected_exitcode = 0;
	test_expected_signal = 0;
	test_expected_linecount = 0;
	test_expected_charcount = 0;
	test_expected_stderr_linecount = 0;
	test_expected_stderr_charcount = 0;
	test_expected_string_return = HELLOSTRING_NL;
	generic_childprocess_test(argv, NULL, TRUE, NULL, 1);
}

/// We produce some output, then kill ourselves with a signal.
/// The output is set up to be captured.
FSTATIC void
test_childprocess_save_command_output_signal(void)
{
	gchar		shell[] = "/bin/sh";
	gchar		dashc[] = "-c";
	// Signal 9 is SIGKILL - should terminate most any process
	gchar		hello[] = "echo \""HELLOSTRING"\"; kill -9 $$";
	gchar* 	argv[] = {shell, dashc, hello, NULL};		// Broken glib API...

	test_expected_death = EXITED_SIGNAL;
	test_expected_exitcode = 0;
	test_expected_signal = 9;
	test_expected_linecount = 0;
	test_expected_charcount = 0;
	test_expected_stderr_linecount = 0;
	test_expected_stderr_charcount = 0;
	test_expected_string_return = HELLOSTRING_NL;
	generic_childprocess_test(argv, NULL, TRUE, NULL, 1);
}
/// We produce some to stderr, and some to stdout
/// Verify capturing the stdout, and the char counts of stderr.
FSTATIC void
test_childprocess_stderr_logging(void)
{
	gchar		shell[] = "/bin/sh";
	gchar		dashc[] = "-c";
	// Signal 9 is SIGKILL - should terminate most any process
	gchar		hello[] = "echo \""HELLOSTRING"\"; echo \""HELLOSTRING"\" >&2";
	gchar* 	argv[] = {shell, dashc, hello, NULL};		// Broken glib API...

	test_expected_death = EXITED_ZERO;
	test_expected_exitcode = 0;
	test_expected_signal = 0;
	test_expected_linecount = 0;
	test_expected_charcount = 0;
	test_expected_stderr_linecount = 1;
	test_expected_stderr_charcount = sizeof(HELLOSTRING);
	test_expected_string_return = HELLOSTRING_NL;
	generic_childprocess_test(argv, NULL, TRUE, NULL, 1);
}

/// This process just exceeds its timeout via a sleep.
/// No output is produced.
FSTATIC void
test_childprocess_timeout(void)
{
	gchar		sleep[] = "/bin/sleep";
	gchar		number[] = "100";
	gchar* 	argv[] = {sleep, number, NULL};		// Broken glib API...

	test_expected_death = EXITED_TIMEOUT;
	test_expected_exitcode = 1;
	test_expected_signal = 0;
	test_expected_linecount = 0;
	test_expected_charcount = 0;
	test_expected_stderr_linecount = 0;
	test_expected_stderr_charcount = 0;
	test_expected_string_return = NULL;
	generic_childprocess_test(argv, NULL, FALSE, NULL, 1);
}

#define	OCFCLASS	"\"" REQCLASSNAMEFIELD		"\": \"ocf\""
#define	LSBCLASS	"\"" REQCLASSNAMEFIELD		"\": \"lsb\""
#define	HBPROVIDER	"\"" REQPROVIDERNAMEFIELD	"\": \"heartbeat\""
#define	DUMMYTYPE	"\"" CONFIGNAME_TYPE		"\": \"Dummy\""
#define	NANOTYPE	"\"" CONFIGNAME_TYPE		"\": \"nanoprobe\""
#define	STARTOP		"\"" REQOPERATIONNAMEFIELD	"\": \"start\""
#define	STOPOP		"\"" REQOPERATIONNAMEFIELD	"\": \"stop\""
#define	MONOP		"\"" REQOPERATIONNAMEFIELD	"\": \"monitor\""
#define	METAOP	"\"" REQOPERATIONNAMEFIELD	"\": \"meta-data\""
#define	RESOURCENAME	"\"" CONFIGNAME_INSTANCE		"\": \"DummyTestGTest01\""
#define	NULLPARAMS	"\"" REQENVIRONNAMEFIELD	"\": {}," "\"" REQCANCELONFAILFIELD	"\": true"
#define	REQID		"\"" REQIDENTIFIERNAMEFIELD	"\": 42"

struct ocf_expect {
	gint		minstrlen;
	gint		maxstrlen;
	enum HowDied	death;
	int		rc;
	int		signal;
	gboolean	coredump;
	gboolean	quit_after_done;
};

FSTATIC void
expect_ocf_callback(ConfigContext* request, gpointer user_data, enum HowDied reason, int rc
,		int signal, gboolean coredump, const char * stringresult)
{
	struct ocf_expect *	expect = (struct ocf_expect *)user_data;
	int			stringlen = (stringresult ? (gint)strlen(stringresult) : -1);

	(void)request;
	if (expect->maxstrlen >= 0) {
		g_assert(stringlen <= expect->maxstrlen);
	}
	g_assert(stringlen >= expect->minstrlen);

	g_assert(reason == expect->death);
	g_assert(rc == expect->rc);
	g_assert(signal == expect->signal);
	g_assert(coredump == expect->coredump);
	if (expect->quit_after_done) {
		g_main_loop_quit(mainloop);
	}
}

FSTATIC void
test_safe_ocfops(void)
{
	const char *	stop =
		"{" OCFCLASS "," DUMMYTYPE "," RESOURCENAME "," STOPOP "," HBPROVIDER "," NULLPARAMS  "}";
	const char *	start =
		"{" OCFCLASS "," DUMMYTYPE "," RESOURCENAME "," STARTOP "," HBPROVIDER "," NULLPARAMS  "}";
	const char *	monitor =
		"{" OCFCLASS "," DUMMYTYPE "," RESOURCENAME "," MONOP "," HBPROVIDER "," NULLPARAMS  "}";
	const char * metadata =
		"{" OCFCLASS "," DUMMYTYPE "," RESOURCENAME "," METAOP "," HBPROVIDER "," NULLPARAMS  "}";
	
	struct ocf_expect success = {
		-1, 		// gint		minstrlen;
		0,		// gint		maxstrlen;
		EXITED_ZERO,	// enum HowDied	death;
		0,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		TRUE,		// quit_after_done
	};
	struct ocf_expect stop_fail = {
		-1, 		// gint		minstrlen;
		0,		// gint		maxstrlen;
		EXITED_NONZERO,	// enum HowDied	death;
		7,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		TRUE,		// quit_after_done
	};

	struct ocf_expect meta_success = {
		200, 		// gint		minstrlen;
		50000,		// gint		maxstrlen;
		EXITED_ZERO,	// enum HowDied	death;
		0,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		TRUE,		// quit_after_done
	};

	const char *		operations[] = 
	{metadata,	stop,     monitor,     start,     monitor,   stop,      monitor };
	struct ocf_expect*	expectations [] =
	{&meta_success,	&success, &stop_fail,  &success,  &success,  &success,  &stop_fail};
	guint	j;

#ifdef HAVE_GETEUID
	if (geteuid() != 0) {
		g_message("Test %s skipped - must be root.", __FUNCTION__);
		return;
	}
#endif

	for (j=0; j < DIMOF(operations); ++j) {
		ResourceCmd*	cmd;
		ConfigContext*	op = configcontext_new_JSON_string(operations[j]);

		g_assert(op != NULL);
		mainloop = g_main_loop_new(g_main_context_default(), TRUE);
		cmd = resourcecmd_new(op, expectations[j], expect_ocf_callback);
		if (NULL == cmd) {
			g_message("Cannot create Dummy OCF resource agent object"
			" -- is the Dummy RA installed? - test %s skipped.", __FUNCTION__);
			no_dummy_RA = TRUE;
			UNREF(op);
			g_main_loop_unref(mainloop);
			return;
		}
		cmd->execute(cmd);
		g_main_loop_run(mainloop);
		g_main_loop_unref(mainloop);
		UNREF(cmd);
		UNREF(op);
	}
	test_all_freed();
}

#define PREFIX	REQID "," OCFCLASS "," DUMMYTYPE "," RESOURCENAME "," HBPROVIDER
FSTATIC void
test_safe_queue_ocfops(void)
{
	const char *	stop =
		"{" PREFIX "," STOPOP "," HBPROVIDER "," NULLPARAMS "}";
	const char *	start =
		"{" PREFIX "," STARTOP "," HBPROVIDER "," NULLPARAMS "}";
	const char *	monitor =
		"{" PREFIX "," MONOP "," HBPROVIDER "," NULLPARAMS "}";
	const char * metadata =
		"{" REQID "," OCFCLASS "," DUMMYTYPE "," RESOURCENAME "," METAOP "," HBPROVIDER "," NULLPARAMS "}";
	
	struct ocf_expect success = {
		-1, 		// gint		minstrlen;
		0,		// gint		maxstrlen;
		EXITED_ZERO,	// enum HowDied	death;
		0,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		FALSE,		// quit_after_done
	};
	struct ocf_expect stop_fail = {
		-1, 		// gint		minstrlen;
		0,		// gint		maxstrlen;
		EXITED_NONZERO,	// enum HowDied	death;
		7,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		FALSE,		// quit_after_done
	};
	struct ocf_expect stop_fail_and_quit = {
		-1, 		// gint		minstrlen;
		0,		// gint		maxstrlen;
		EXITED_NONZERO,	// enum HowDied	death;
		7,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		TRUE,		// quit_after_done
	};

	struct ocf_expect meta_success = {
		200, 		// gint		minstrlen;
		50000,		// gint		maxstrlen;
		EXITED_ZERO,	// enum HowDied	death;
		0,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		FALSE,		// quit_after_done
	};

	const char *		operations[] = 
	{metadata,	stop,     monitor,     start,     monitor,   stop,      monitor };
	struct ocf_expect*	expectations [] =
	{&meta_success,	&success, &stop_fail,  &success,  &success,  &success,  &stop_fail_and_quit};

	guint			j;
	ResourceQueue*		rscq;

#ifdef HAVE_GETEUID
	if (geteuid() != 0) {
		g_message("Test %s skipped - must be root.", __FUNCTION__);
		return;
	}
#endif
	if (no_dummy_RA) {
		g_message("Apparently No dummy RA - installed - test %s skipped.", __FUNCTION__);
		return;
	}
	//proj_class_incr_debug(NULL);
	//proj_class_incr_debug(NULL);
	//proj_class_incr_debug(NULL);

	rscq = resourcequeue_new(0);
	mainloop = g_main_loop_new(g_main_context_default(), TRUE);
	// Queue all the commands up at once, then run them
	for (j=0; j < DIMOF(operations); ++j) {
		ConfigContext*	op = configcontext_new_JSON_string(operations[j]);
		g_assert(op != NULL);
		g_assert(rscq->Qcmd(rscq, op, expect_ocf_callback, expectations[j]) == TRUE);
		UNREF(op);
	}
	g_main_loop_run(mainloop);
	g_main_loop_unref(mainloop);
	UNREF(rscq); rscq = NULL;
	test_all_freed();
}

#define LSBPREFIX	REQID "," LSBCLASS "," NANOTYPE "," RESOURCENAME

FSTATIC void
test_safe_queue_lsbops(void)
{
	const char *	stop =
		"{" LSBPREFIX "," STOPOP "," NULLPARAMS "}";
	const char *	start =
		"{" LSBPREFIX "," STARTOP "," NULLPARAMS "}";
	const char *	monitor =
		"{" LSBPREFIX "," MONOP "," NULLPARAMS "}";
	const char * metadata =
		"{" LSBPREFIX "," METAOP "," NULLPARAMS "}";
	
	struct ocf_expect success = {
		-1, 		// gint		minstrlen;
		0,		// gint		maxstrlen;
		EXITED_ZERO,	// enum HowDied	death;
		0,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		FALSE,		// quit_after_done
	};
	struct ocf_expect stop_fail = {
		-1, 		// gint		minstrlen;
		0,		// gint		maxstrlen;
		EXITED_NONZERO,	// enum HowDied	death;
		7,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		FALSE,		// quit_after_done
	};
	struct ocf_expect stop_fail_and_quit = {
		-1, 		// gint		minstrlen;
		0,		// gint		maxstrlen;
		EXITED_NONZERO,	// enum HowDied	death;
		7,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		TRUE,		// quit_after_done
	};

	struct ocf_expect meta_success = {
		200, 		// gint		minstrlen;
		50000,		// gint		maxstrlen;
		EXITED_ZERO,	// enum HowDied	death;
		0,		// int		rc;
		0,		// int		signal;
		FALSE,		// gboolean	coredump;
		FALSE,		// quit_after_done
	};

	const char *		operations[] = 
	{metadata,	stop,     monitor,     start,     monitor,   stop,      monitor };
	struct ocf_expect*	expectations [] =
	{&meta_success,	&success, &stop_fail,  &success,  &success,  &success,  &stop_fail_and_quit};

	guint			j;
	ResourceQueue*		rscq;
	const char *		initpath = LSB_ROOT "/nanoprobe";

#ifdef HAVE_GETEUID
	if (geteuid() != 0) {
		g_message("Test %s skipped - must be root.", __FUNCTION__);
		return;
	}
#endif
	if (	!g_file_test(initpath, G_FILE_TEST_IS_REGULAR)
	||	!g_file_test(initpath, G_FILE_TEST_IS_EXECUTABLE)) {
		g_message("Test %s skipped No LSB Resource agent [%s]", __FUNCTION__, initpath);
		return;
	}

	//proj_class_incr_debug(NULL);
	//proj_class_incr_debug(NULL);
	//proj_class_incr_debug(NULL);

	rscq = resourcequeue_new(0);
	mainloop = g_main_loop_new(g_main_context_default(), TRUE);
	// Queue all the commands up at once, then run them
	for (j=0; j < DIMOF(operations); ++j) {
		ConfigContext*	op = configcontext_new_JSON_string(operations[j]);
		g_assert(op != NULL);
		//g_message("Running operation %d: %s", j, operations[j]);
		g_assert(rscq->Qcmd(rscq, op, expect_ocf_callback, expectations[j]) == TRUE);
		UNREF(op);
	}
	g_main_loop_run(mainloop);
	g_main_loop_unref(mainloop);
	UNREF(rscq); rscq = NULL;
	test_all_freed();
}

/// Test main program ('/gtest01') using the glib test fixtures
int
main(int argc, char ** argv)
{
	gboolean	can_kill;
#if 0
	#ifdef HAVE_MCHECK_PEDANTIC
		// Unfortunately, even being the first code in main is not soon enough :-(
		g_assert(mcheck_pedantic(NULL) == 0);
	#else
	#	ifdef HAVE_MCHECK
		g_assert(mcheck(NULL) == 0);
	#	endif
	#endif
#endif
	// Processes run as part of "docker build" can't kill(2) any processes
	can_kill = (kill(getpid(), 0) == 0);
	if (!can_kill) {
		g_message("Tests that kill processes not run.");
	}
	g_setenv("G_MESSAGES_DEBUG", "all", TRUE);
	g_test_init(&argc, &argv, NULL);
	g_test_add_func("/gtest01/gmain/command-output", test_read_command_output_at_EOF);
	g_test_add_func("/gtest01/gmain/log-command-output", test_log_command_output);
	g_test_add_func("/gtest01/gmain/childprocess_log_all", test_childprocess_log_all);
	g_test_add_func("/gtest01/gmain/childprocess_false", test_childprocess_false);
	if (can_kill) {
		g_test_add_func("/gtest01/gmain/childprocess_timeout", test_childprocess_timeout);
	}
	g_test_add_func("/gtest01/gmain/childprocess_save_command_output"
	,	test_childprocess_save_command_output);
	if (can_kill) {
		g_test_add_func("/gtest01/gmain/childprocess_save_command_output_timeout"
		,	test_childprocess_save_command_output_timeout);
		g_test_add_func("/gtest01/gmain/childprocess_save_command_output_signal"
		,	test_childprocess_save_command_output_signal);
	}
	g_test_add_func("/gtest01/gmain/childprocess_stderr_logging"
	,	test_childprocess_stderr_logging);
	g_test_add_func("/gtest01/gmain/childprocess_modenv", test_childprocess_modenv);
	g_test_add_func("/gtest01/gmain/safe_ocfops", test_safe_ocfops);
	g_test_add_func("/gtest01/gmain/safe_queue_ocfops", test_safe_queue_ocfops);
#if 0
	// LSB status operation is broken under systemd.
	g_test_add_func("/gtest01/gmain/safe_queue_lsbops", test_safe_queue_lsbops);
#endif
	return g_test_run();
}
