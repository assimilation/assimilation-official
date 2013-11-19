/**
@page SourceAndLicense Source Availability and License Terms

@section LicenseTerms License Terms
The version of the source from which these documents were created is licensed under the GNU General Public License (GPL) version 3 or any later version at your option.
Please note that any discovery or monitoring scripts that you author
<i>are not required to be under the GPL</i> because they are invoked through fork and exec not through library linking.
If you want the project to include them in our distributions, they will be provided to others under the GPL.
Modifications to the core of the system are covered under the GPL.

All contributions to the project are covered by a contributor agreement.
The rationale for this agreement is explained on
<a href="http://techthoughts.typepad.com/managing_computers/2013/04/does-the-gpl-really-work.html">our blog</a>.

If there are any source files which are not marked in this fashion, it is a clerical error.
Those files are also provided under these same terms.

@section SourceLocation Where To Find The Current Project Source
As of this writing, the source to the latest version of this software is stored under Mercurial
and can be found at http://hg.linux-ha.org/
or more specifically at <a href="http://hg.linux-ha.org/assimilation/">http://hg.linux-ha.org/assimilation/</a>.
You can get your own copy of the Mercurial repository using this command:
@code
  hg clone http://hg.linux-ha.org/assimilation/
@endcode

You can get and install the absolute latest tar ball using this command:
@code
   wget http://hg.linux-ha.org/assimilation/raw-file/tip/buildtools/assimDnI
@endcode
Note that this does not require that you have a copy of Mercurical.
If you do not have the <i>wget</i> command, you can save that URL using your favorite browser instead.

An online version of these documents that corresponds to the latest version of the source can be found here:
http://linux-ha.org/source-doc/assimilation/html/index.html

@page Contributing Contributing to the Project
Interested in contributing to the Assimilation Project?
Then you've come to the right place!

Here are the steps you'll need to take to become a contributor to the Assimilation project:
- Join the Assimilation Mailing List
- Get a copy of Mercurial from http://mercurial.selenic.com
- Clone the repository at http://hg.linux-ha.org/assimilation/
- Sign the Assimilation Contributor Agreement as described below
- Discuss your ideas and on the mailing list
- Create a patch implementing your ideas following project standards
- Send Mercurial patches of your contributions to the Assimilation mailing list
- Discuss on the mailing list

@section WhyAContributorAgreement Why A Contributor Agreement?
Contributor agreements are provided for a few reasons:
- Ensure the legal integrity of the project - so that everyone asserts that they're providing original code to the project.
  This protects users and other contributors.
- Create a single legal entity that could easily enforce terms of the licenses.
- Ensure that no one is submitting code that they know to be covered by patents, and dealing with the cases where there might be such patents.
- Provide for the ability to change licenses in the future.  Depending on the future legal landscape, it might prove desirable
  to switch licenses at some time in the future.
  In addition, it creates the possibility to offer supported commercial versions
  of the project under a different license in order to provide better support for the project
  and its users.

@section ContributorAgreement The Assimilation Contributor Agreement
The Assimilation project's contributor agreements are borrowed from the <a href="http://harmonyagreements.org">Harmony Project</a>
agreements.  They provide an excellent <a href="http://harmonyagreements.org/guide.html">guide</a> to understanding
these contributor agreements.

Note that this agreement creates a rights sharing arrangement with the project.
<i>You do not lose any rights to use or relicense your contribution any way you wish by signing this contribution agreement</i>.

- http://hg.linux-ha.org/assimilation/raw-file/tip/legal/AssimilationIndividualContributorAgreement-v1.0.pdf - md5 sum 15fff2cc37118835f98827ffd84b8288
- http://hg.linux-ha.org/assimilation/raw-file/tip/legal/AssimilationEntityContributorAgreement-v1.0.pdf -     md5 sum df2793e8d13e4df7001a5b88a15fd06f

@section SigningContributorAgreement How to Provide a Signed Copy of the Contributor Agreement
There are two ways to provide a signed copy of the agreement:
@subsection PrintedAgreement Printed Agreement
- Print off a copy of the relevant agreement (individual or entity)
- Read it carefully and agree to its terms
- Sign it
- Scan the entire unmodified agreement in as a single PDF with a resolution of 200 pixels/inch or more.
- Email a copy of it to <a href="mailto:AssimilationSystems@gmail.com">&lt;AssimilationSystems@gmail.com&gt; Assimilation Systems Limited</a>.
@subsection EmailedAgreement Emailed Agreement
This method is only available if you can digitally sign emails using a well-known public key.
- Download and read the document carefully and agree to its terms
- Send a digitally signed email described below to <a href="mailto:AssimilationSystems@gmail.com">&lt;AssimilationSystems@gmail.com&gt; Assimilation Systems Limited</a>.
 - Attach the PDF of the unmodified agreement from the web site
 - In the body of the email put these statements

  <tt>
  I have read and agree to the terms of the attached document for contributions to the Assimilation Project
  (represented by Assimilation Systems Limited).
  
  Submitting this digitally signed email to Assimilation Systems Limited constitutes my acceptance of the terms of the attached agreement
  and I provide this email as a legally binding signature to the unmodified agreement attached to this signed email.

  <i>Your Name and email address</i>

  <i>Today's date</i>
  </tt>

@section WhatIsAssimilationSystemsLimited What Is Assimilation Systems Limited?
When you read the agreement, you'll notice that the Assimilation Project contributor agreements are with Assimilation Systems Limited,
not with an individual.
The project founder (Alan Robertson) created Assimilation Systems Limited as a perpetual legal entity to be the
owner of the rights vested in the project.  It is a Limited Liability Company established and registered in Colorado, USA.

@page NonOwnedSoftware Contributing Software You Don't Own

At this time we do not have a method of contributing software you do not own the Copyright to
the entire work of authorship.  If this is the case for a contribution you wish to provide
to the project, please discuss this on the project mailing list.

*/
/**
@page ContactInfo Contact Information 
@section ContactInfoSection Contact Information
- Development mailing list http://lists.community.tummy.com/cgi-bin/mailman/listinfo/assim-devel
   list archives <a href="http://lists.community.tummy.com/pipermail/assim-devel/">pipermail</a>.
- General project mailing list http://lists.community.tummy.com/cgi-bin/mailman/listinfo/assimilation
 - list archives <a href="http://dir.gmane.org/gmane.comp.monitoring.assimilation">Gmane</a> or
   <a href="http://lists.community.tummy.com/pipermail/assimilation/">pipermail</a>.
http://lists.community.tummy.com/cgi-bin/mailman/listinfo/assim-devel
- Project Twitter Hash Tag  \#AssimMon
- Project Web Site	http://assimmon.org/
- Alan Robertson - email: alanr@@unix.sh - Twitter: @@OSSAlanR
- Roger Massey - email: sadsaddle (a) gmail (and-the-usual-ending) - Twitter @@rhm84119
*/
