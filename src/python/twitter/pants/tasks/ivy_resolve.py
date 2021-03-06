# ==================================================================================================
# Copyright 2011 Twitter, Inc.
# --------------------------------------------------------------------------------------------------
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this work except in compliance with the License.
# You may obtain a copy of the License in the LICENSE file, or at:
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==================================================================================================

from __future__ import print_function
from collections import defaultdict

import os
import shutil
import time

from twitter.common.dirutil import safe_mkdir
from twitter.pants import binary_util
from twitter.pants.ivy.bootstrapper import Bootstrapper
from .cache_manager import VersionedTargetSet
from .ivy_utils import IvyUtils
from .nailgun_task import NailgunTask
from . import TaskError


class IvyResolve(NailgunTask):

  @classmethod
  def setup_parser(cls, option_group, args, mkflag):
    NailgunTask.setup_parser(option_group, args, mkflag)

    flag = mkflag('override')
    option_group.add_option(flag, action='append', dest='ivy_resolve_overrides',
                            help="""Specifies a jar dependency override in the form:
                            [org]#[name]=(revision|url)

                            For example, to specify 2 overrides:
                            %(flag)s=com.foo#bar=0.1.2 \\
                            %(flag)s=com.baz#spam=file:///tmp/spam.jar
                            """ % dict(flag=flag))

    report = mkflag("report")
    option_group.add_option(report, mkflag("report", negate=True), dest = "ivy_resolve_report",
                            action="callback", callback=mkflag.set_bool, default=False,
                            help = "[%default] Generate an ivy resolve html report")

    option_group.add_option(mkflag("open"), mkflag("open", negate=True),
                            dest="ivy_resolve_open", default=False,
                            action="callback", callback=mkflag.set_bool,
                            help="[%%default] Attempt to open the generated ivy resolve report "
                                 "in a browser (implies %s)." % report)

    option_group.add_option(mkflag("outdir"), dest="ivy_resolve_outdir",
                            help="Emit ivy report outputs in to this directory.")

    option_group.add_option(mkflag("args"), dest="ivy_args", action="append", default=[],
                            help = "Pass these extra args to ivy.")

    option_group.add_option(mkflag("mutable-pattern"), dest="ivy_mutable_pattern",
                            help="If specified, all artifact revisions matching this pattern will "
                                 "be treated as mutable unless a matching artifact explicitly "
                                 "marks mutable as False.")

  def __init__(self, context, confs=None):
    super(IvyResolve, self).__init__(context)
    work_dir = context.config.get('ivy-resolve', 'workdir')

    self._ivy_bootstrapper = Bootstrapper.instance()
    self._cachedir = self._ivy_bootstrapper.ivy_cache_dir
    self._confs = confs or context.config.getlist('ivy-resolve', 'confs', default=['default'])
    self._classpath_dir = os.path.join(work_dir, 'mapped')

    self._outdir = context.options.ivy_resolve_outdir or os.path.join(work_dir, 'reports')
    self._open = context.options.ivy_resolve_open
    self._report = self._open or context.options.ivy_resolve_report

    self._ivy_bootstrap_key = 'ivy'
    ivy_bootstrap_tools = context.config.getlist('ivy-resolve', 'bootstrap-tools', ':xalan')
    self._jvm_tool_bootstrapper.register_jvm_tool(self._ivy_bootstrap_key, ivy_bootstrap_tools)

    self._ivy_utils = IvyUtils(config=context.config,
                               options=context.options,
                               log=context.log)
    context.products.require_data('exclusives_groups')

    # Typically this should be a local cache only, since classpaths aren't portable.
    self.setup_artifact_cache_from_config(config_section='ivy-resolve')

  def invalidate_for(self):
    return self.context.options.ivy_resolve_overrides

  def execute(self, targets):
    """Resolves the specified confs for the configured targets and returns an iterator over
    tuples of (conf, jar path).
    """
    groups = self.context.products.get_data('exclusives_groups')
    executor = self.create_java_executor()

    # Below, need to take the code that actually execs ivy, and invoke it once for each
    # group. Then after running ivy, we need to take the resulting classpath, and load it into
    # the build products.

    # The set of groups we need to consider is complicated:
    # - If there are no conflicting exclusives (ie, there's only one entry in the map),
    #   then we just do the one.
    # - If there are conflicts, then there will be at least three entries in the groups map:
    #   - the group with no exclusives (X)
    #   - the two groups that are in conflict (A and B).
    # In the latter case, we need to do the resolve twice: Once for A+X, and once for B+X,
    # because things in A and B can depend on things in X; and so they can indirectly depend
    # on the dependencies of X.
    # (I think this well be covered by the computed transitive dependencies of
    # A and B. But before pushing this change, review this comment, and make sure that this is
    # working correctly.)
    for group_key in groups.get_group_keys():
      # Narrow the groups target set to just the set of targets that we're supposed to build.
      # Normally, this shouldn't be different from the contents of the group.
      group_targets = groups.get_targets_for_group_key(group_key) & set(targets)

      # NOTE(pl): The symlinked ivy.xml (for IDEs, particularly IntelliJ) in the presence of
      # multiple exclusives groups will end up as the last exclusives group run.  I'd like to
      # deprecate this eventually, but some people rely on it, and it's not clear to me right now
      # whether telling them to use IdeaGen instead is feasible.
      classpath = self.ivy_resolve(group_targets,
                                   executor=executor,
                                   symlink_ivyxml=True,
                                   workunit_name='ivy-resolve')
      if self.context.products.is_required_data('ivy_jar_products'):
        self._populate_ivy_jar_products(group_targets)
      for conf in self._confs:
        # It's important we add the full classpath as an (ordered) unit for code that is classpath
        # order sensitive
        classpath_entries = map(lambda entry: (conf, entry), classpath)
        groups.update_compatible_classpaths(group_key, classpath_entries)

      if self._report:
        self._generate_ivy_report(group_targets)

    create_jardeps_for = self.context.products.isrequired('jar_dependencies')
    if create_jardeps_for:
      genmap = self.context.products.get('jar_dependencies')
      for target in filter(create_jardeps_for, targets):
        self._ivy_utils.mapjars(genmap, target, executor=executor,
                                workunit_factory=self.context.new_workunit)

  def check_artifact_cache_for(self, invalidation_check):
    # Ivy resolution is an output dependent on the entire target set, and is not divisible
    # by target. So we can only cache it keyed by the entire target set.
    global_vts = VersionedTargetSet.from_versioned_targets(invalidation_check.all_vts)
    return [global_vts]

  def _populate_ivy_jar_products(self, targets):
    """Populate the build products with an IvyInfo object for each generated ivy report."""
    ivy_products = self.context.products.get_data('ivy_jar_products') or defaultdict(list)
    for conf in self._confs:
      ivyinfo = self._ivy_utils.parse_xml_report(targets, conf)
      if ivyinfo:
        # Value is a list, to accommodate multiple exclusives groups.
        ivy_products[conf].append(ivyinfo)
    self.context.products.safe_create_data('ivy_jar_products', lambda: ivy_products)

  def _generate_ivy_report(self, targets):
    def make_empty_report(report, organisation, module, conf):
      no_deps_xml_template = """
        <?xml version="1.0" encoding="UTF-8"?>
        <?xml-stylesheet type="text/xsl" href="ivy-report.xsl"?>
        <ivy-report version="1.0">
          <info
            organisation="%(organisation)s"
            module="%(module)s"
            revision="latest.integration"
            conf="%(conf)s"
            confs="%(conf)s"
            date="%(timestamp)s"/>
        </ivy-report>
      """
      no_deps_xml = no_deps_xml_template % dict(organisation=organisation,
                                                module=module,
                                                conf=conf,
                                                timestamp=time.strftime('%Y%m%d%H%M%S'))
      with open(report, 'w') as report_handle:
        print(no_deps_xml, file=report_handle)

    classpath = self._jvm_tool_bootstrapper.get_jvm_tool_classpath(self._ivy_bootstrap_key,
                                                                   self.create_java_executor())

    reports = []
    org, name = self._ivy_utils.identify(targets)
    xsl = os.path.join(self._cachedir, 'ivy-report.xsl')

    # Xalan needs this dir to exist - ensure that, but do no more - we have no clue where this
    # points.
    safe_mkdir(self._outdir, clean=False)

    for conf in self._confs:
      params = dict(org=org, name=name, conf=conf)
      xml = self._ivy_utils.xml_report_path(targets, conf)
      if not os.path.exists(xml):
        make_empty_report(xml, org, name, conf)
      out = os.path.join(self._outdir, '%(org)s-%(name)s-%(conf)s.html' % params)
      args = ['-IN', xml, '-XSL', xsl, '-OUT', out]
      if 0 != self.runjava(classpath=classpath, main='org.apache.xalan.xslt.Process',
                           args=args, workunit_name='report'):
        raise TaskError
      reports.append(out)

    css = os.path.join(self._outdir, 'ivy-report.css')
    if os.path.exists(css):
      os.unlink(css)
    shutil.copy(os.path.join(self._cachedir, 'ivy-report.css'), self._outdir)

    if self._open:
      binary_util.ui_open(*reports)
