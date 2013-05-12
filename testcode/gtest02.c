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
#include <string.h>
#include <resourcecmd.h>

FSTATIC void test_invalid_resourcecmd(void);
FSTATIC gboolean logfatal_function(const gchar*, GLogLevelFlags, const gchar*,gpointer);

FSTATIC gboolean
logfatal_function(
	const gchar *	log_domain
,	GLogLevelFlags	log_level
,	const gchar *	message
,	gpointer	user_data)
{
	const char **	messagelist = (const char **)user_data;

	const char **	mptr;

	(void)log_domain;
	(void)log_level;

	for (mptr = messagelist; mptr && *mptr; ++mptr) {
		if (strstr(message, *mptr) != NULL) {
			return FALSE;
		}
	}
	return TRUE;
}

///< Try various invalid resource command initializers
FSTATIC void
test_invalid_resourcecmd(void)
{
	const char *	json_cmds[] = {
		"{}",
		"{\"" REQCLASSNAMEFIELD "\": \"NOSUCHRESOURCECLASS\"}",
		NULL
	};
	const char *	expected_failures[] = {
		": No class name in request [{}]",
		": Invalid resource class [NOSUCHRESOURCECLASS]",
		": NULL resourcecmd request",
		NULL
	};
	guint		j;

	g_log_set_fatal_mask(G_LOG_DOMAIN, 0);
	g_test_log_set_fatal_handler (logfatal_function, expected_failures);

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
}

/// Test main program ('/gtest02') using the glib test fixtures
int
main(int argc, char ** argv)
{
	g_setenv("G_MESSAGES_DEBUG", "all", TRUE);
	g_test_init(&argc, &argv, NULL);
	g_test_add_func("/gtest02/test_invalid_resourcecmd", test_invalid_resourcecmd);
	return g_test_run();
}
