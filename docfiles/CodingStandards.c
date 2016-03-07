/**
@page CodingStandards Assimilation Coding Standards
This page is a start to an evolving set of written coding standards.
@section General_Coding_Standards General Coding Guidelines
- All major new features need tests - each according to the way they're done for that language.
  Most tests in this project should be incorporated into the standard unit tests which are always
  executed on every platform before being incorporated.
  These tests are run for one environment on Travis.ci as each patch is incorporated.
  There is also a semi-hack script called <i>checkandput</i> which I use before I push anything
  upstream. Feel free to improve it, or write your own.
- All code must be (C) Assimilation Systems Limited
- Contributors must have signed the contributor agreement.
- All code and documentation makes and installs with Cmake.
- Git commits require meaningful comments, and anything non-trivial must reference a Trello issue
  by URL, or a GitHub issue using GitHub standards.
@section Shell_Coding_Standards Shell Coding Standards
- All code must conform to POSIX shell syntax. No Bourne-Again (or other) shell extensions.
- Code must be indented 4 spaces, using spaces only. No tab indentation.
- Code must minimize its external dependencies - try to use commands which are universally available.
- Code must have a header based on the buildtools/boilerplate.sh file.
@section C_Coding_Standards C Coding Standards
- C code is indented using tabs with tabs being 8 characters.
- Lines of C code should generally be restricted to no more than 100 characters.
- Code must have a header based on the buildtools/boilerplate.c file.
- Code must be documented in a way that's compatible with Doxygen.
- The keyword "else" is spelled "}else{". All if statements should be fully bracketed.
- Function names in function definitions begin against the left margin.
- Opening curly braces ("{") belong on the end of the line of the control statement, function definition, etc.
  Initialization of variables aren't required to do that.
- Generally \#ifdefs in \#define statements are preferred of \#ifdefs in code.
- \#ifdefs on features are preferred over \#ifdefs based on platform.
- All code must pass our strict warnings on compile with zero warnings. No exceptions.
- All code must pass the Clang static analyzer with zero warnings. No exceptions.
- All code should pass the coverity static analyzer with zero warnings.
  Limited exceptions can be made for false positives, but they must be extensively discussed
  and mutually agreed to.
  Code changes to make the warning go away are <i>strongly</i> preferred over exceptions in coverity,
  but sometimes that's impractical or not possible.
  Exeptions will only be made for cases where the analyzer is wrong, or where it's universally agreed
  that making it go away is impractical or impossible.
- Any new dynamically allocated data structure should be created using the AssimObj object-oriented
  class system.
- New classes must be documented in a way that's compatible with our conventions regarding Doxygen
  and our own C-class system.
- All production programs should free all their objects and verify that they're all free on exiting.
  If the number of allocated objects isn't zero, it should exit with a non-zero code unless there
  is a reason this will cause problems to other programs.
- All code written as part a nanoprobe must compile without errors or warnings on Windows.
  Currently that's the same as "is expected to compile without warnings or errors on Windows".
- All nanoprobe code written should run on any POSIX system and also on Windows unless there's a reason
  why this particular function could never be performed on Windows at all.
  Please learn about the portability functions in <i>glib2</i>.
- The only libraries which can be used in nanoprobe code are: libc, glib2, libpcap/winpcap and libsodium.
- All tests should verify that there all objects are freed on exiting, and must <i>always</i> exit
  non-zero if there are remaining objects at the end.
@section Python_Coding_Standards Python Coding Standards
- Code must have a header based on the buildtools/boilerplate.sh file.
- Code must be indented 4 spaces, using spaces only. No tab indentation.
- Human-written code must pass pylint with our project rules with zero warnings.
  Writing override rules in the code is acceptable, but discouraged.
  Some of the earliest code in the system has more than it should because I didn't
  know enough about how to make the warnings go away.
*/
