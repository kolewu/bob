# Bob build tool
# Copyright (C) 2016 BobBuildTool team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from unittest import TestCase

import os
import subprocess
import tempfile

from bob.input import GitScm
from bob.utils import removePath

class TestGitScmStatus(TestCase):
    repodir = ""
    repodir_local = ""

    def callGit(self, *arg, **kwargs):
        try:
            subprocess.check_output(*arg, shell=True, universal_newlines=True, stderr=subprocess.STDOUT, **kwargs)
        except subprocess.CalledProcessError as e:
            self.fail("git error: '{}' '{}'".format(arg, e.output))

    def tearDown(self):
        removePath(self.repodir)
        removePath(self.repodir_local)

    def setUp(self):
        self.repodir = tempfile.mkdtemp()
        self.repodir_local = tempfile.mkdtemp()

        self.callGit('git init', cwd=self.repodir)

        # setup user name and email for travis
        self.callGit('git config user.email "bob@bob.bob"', cwd=self.repodir)
        self.callGit('git config user.name test', cwd=self.repodir)

        f = open(os.path.join(self.repodir, "test.txt"), "w")
        f.write("hello world")
        f.close()
        self.callGit('git add test.txt', cwd=self.repodir)
        self.callGit('git commit -m "first commit"', cwd=self.repodir)

        self.callGit('git clone ' + self.repodir + ' ' + self.repodir_local, cwd='/tmp')

        # setup user name and email for travis
        self.callGit('git config user.email "bob@bob.bob"', cwd=self.repodir_local)
        self.callGit('git config user.name test', cwd=self.repodir_local)

    def testBranch(self):
        s = GitScm({ 'scm' : "git", 'url' : self.repodir, 'branch' : 'anybranch', 'recipe' : "foo.yaml#0" })
        self.assertEqual(s.status(self.repodir_local, '')[0], 'dirty')

    def testClean(self):
        s = GitScm({ 'scm' : "git", 'url' : self.repodir, 'recipe' : "foo.yaml#0" })
        self.assertEqual(s.status(self.repodir_local, '')[0], 'clean')

    def testCommit(self):
        s = GitScm({ 'scm' : "git", 'url' : self.repodir,
            'commit' : '0123456789012345678901234567890123456789', 'recipe' : "foo.yaml#0" })
        self.assertEqual(s.status(self.repodir_local, '')[0], 'dirty')

    def testEmpty(self):
        removePath(self.repodir_local)
        s = GitScm({ 'scm' : "git", 'url' : self.repodir, 'recipe' : "foo.yaml#0" })
        self.assertEqual(s.status(self.repodir_local, '')[0], 'empty')

    def testModified(self):
        f = open(os.path.join(self.repodir_local, "test.txt"), "w")
        f.write("test modified")
        f.close()
        s = GitScm({ 'scm' : "git", 'url' : self.repodir, 'recipe' : "foo.yaml#0" })
        self.assertEqual(s.status(self.repodir_local, '')[0], 'dirty')

    def testTag(self):
        s = GitScm({ 'scm' : "git", 'url' : self.repodir, 'tag' : 'v0.1', 'recipe' : "foo.yaml#0" })
        self.assertEqual(s.status(self.repodir_local, '')[0], 'dirty')

    def testUnpushed(self):
        f = open(os.path.join(self.repodir_local, "test.txt"), "w")
        f.write("test modified")
        f.close()
        self.callGit('git commit -a -m "modified"', cwd=self.repodir_local)

        s = GitScm({ 'scm' : "git", 'url' : self.repodir, 'recipe' : "foo.yaml#0" })
        self.assertEqual(s.status(self.repodir_local, '')[0], 'dirty')

    def testUrl(self):
        s = GitScm({ 'scm' : "git", 'url' : 'anywhere', 'recipe' : "foo.yaml#0" })
        self.assertEqual(s.status(self.repodir_local, '')[0], 'dirty')

