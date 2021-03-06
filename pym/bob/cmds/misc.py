# -*- coding: utf-8 -*-

# Bob build tool
# Copyright (C) 2016  TechniSat Digital GmbH
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

from ..input import RecipeSet
from ..errors import BuildError
import argparse
import codecs
import sys

try:
    # test if stdout can handle box drawing characters
    codecs.encode("└├│─", sys.stdout.encoding)
    LS_SEP_1 = u"└── "
    LS_SEP_2 = u"├── "
    LS_SEP_3 = u"    "
    LS_SEP_4 = u"│   "
except UnicodeEncodeError:
    # fall back to ASCII
    LS_SEP_1 = "\\-- "
    LS_SEP_2 = "|-- "
    LS_SEP_3 = "    "
    LS_SEP_4 = "|   "


def doLS(argv, bobRoot):
    def showTree(package, showAll, showOrigin, prefix=""):
        i = 0
        if showAll:
            packages = { name : (child.node, child.origin) for (name, child) in package.items() }
        else:
            packages = { name : (child.node, child.origin) for (name, child) in package.items() if child.direct }
        for n,(p,o) in sorted(packages.items()):
            last = (i >= len(packages)-1)
            print("{}{}{}{}".format(prefix, LS_SEP_1 if last else LS_SEP_2, n,
                " ({})".format(o) if (showOrigin and o) else ""))
            showTree(p, showAll, showOrigin, prefix + (LS_SEP_3 if last else LS_SEP_4))
            i += 1

    def showPrefixed(package, recurse, showAll, showOrigin, showAliases, stack, level=0):
        if showAll:
            packages = { name : (child.node, child.origin) for (name, child) in package.items() }
        else:
            packages = { name : (child.node, child.origin) for (name, child) in package.items() if child.direct }
        for p in showAliases: print(p)
        for n,(p,o) in sorted(packages.items()):
            newStack = stack[:]
            newStack.append(n)
            print("{}{}".format("/".join(newStack),
                                " ({})".format(o) if (showOrigin and o) else ""))
            if recurse:
                showPrefixed(p, recurse, showAll, showOrigin, [], newStack, level+1)

    parser = argparse.ArgumentParser(prog="bob ls", description='List packages.')
    parser.add_argument('package', type=str, nargs='?', default="",
                        help="Sub-package to start listing from")
    parser.add_argument('-a', '--all', default=False, action='store_true',
                        help="Show indirect dependencies too")
    parser.add_argument('-o', '--origin', default=False, action='store_true',
                        help="Show origin of indirect dependencies")
    parser.add_argument('-r', '--recursive', default=False, action='store_true',
                        help="Recursively display dependencies")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-p', '--prefixed', default=False, action='store_true',
                       help="Prints the full path prefix for each package")
    group.add_argument('-d', '--direct', default=False, action='store_true',
                       help="List packages themselves, not their contents")
    parser.add_argument('-D', default=[], action='append', dest="defines",
        help="Override default environment variable")
    parser.add_argument('-c', dest="configFile", default=[], action='append',
        help="Use config File")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--sandbox', action='store_true', default=False,
        help="Enable sandboxing")
    group.add_argument('--no-sandbox', action='store_false', dest='sandbox',
        help="Disable sandboxing")
    args = parser.parse_args(argv)

    defines = {}
    for define in args.defines:
        d = define.split("=")
        if len(d) == 1:
            defines[d[0]] = ""
        elif len(d) == 2:
            defines[d[0]] = d[1]
        else:
            parser.error("Malformed define: "+define)

    recipes = RecipeSet()
    recipes.setConfigFiles(args.configFile)
    recipes.parse()

    showAll = args.all
    showOrigin = args.origin
    packages = recipes.generatePackages(lambda s,m: "unused", defines, args.sandbox)
    showAliases = packages.getAliases() if args.package == "" else []

    for (stack, root) in packages.queryTreePath(args.package):
        if args.prefixed:
            showPrefixed(root, args.recursive, showAll, showOrigin, showAliases, stack)
        elif args.direct:
            print("/".join(stack) if stack else "/")
        elif args.recursive:
            print("/".join(stack) if stack else "/")
            showTree(root, showAll, showOrigin)
        else:
            showPrefixed(root, False, showAll, showOrigin, showAliases, [])

class Default(dict):
    def __init__(self, default, *args, **kwargs):
        self.__default = default
        super().__init__(*args, **kwargs)

    def __missing__(self, key):
        return self.__default

def doQueryMeta(argv, bobRoot):
    parser = argparse.ArgumentParser(prog="bob query-meta",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""Query meta information of packages.""")
    parser.add_argument('packages', nargs='+', help="(Sub-)packages to query")
    parser.add_argument('-D', default=[], action='append', dest="defines",
        help="Override default environment variable")
    parser.add_argument('-c', dest="configFile", default=[], action='append',
        help="Use config File")
    parser.add_argument('-r', '--recursive', default=False, action='store_true',
                        help="Recursively display dependencies")
    args = parser.parse_args(argv)

    defines = {}
    for define in args.defines:
        d = define.split("=")
        if len(d) == 1:
            defines[d[0]] = ""
        elif len(d) == 2:
            defines[d[0]] = d[1]
        else:
            parser.error("Malformed define: "+define)

    recipes = RecipeSet()
    recipes.setConfigFiles(args.configFile)
    recipes.parse()
    packages = recipes.generatePackages(lambda s,m: "unused", defines)

    def showPackage(package, recurse, done):
        # Show each package only once. Meta variables are fixed and not variant
        # dependent.
        key = package.getName()
        if key not in done:
            for (var, val) in package.getMetaEnv().items():
                print(package.getName() + " " + var + "=" + val)
            done.add(key)

        # recurse package tree if requested
        if recurse:
            for ps in package.getDirectDepSteps():
                showPackage(ps.getPackage(), recurse, done)

    done = set()
    for p in args.packages:
        for package in packages.queryPackagePath(p):
            showPackage(package, args.recursive, done)

def doQuerySCM(argv, bobRoot):
    parser = argparse.ArgumentParser(prog="bob query-scm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Query SCM configuration of packages.

By default this command will print one line for each SCM in the given package.
The output format may be overridded by '-f'. By default the following formats
are used:

 * git="git {package} {dir} {url} {branch}"
 * svn="svn {package} {dir} {url} {revision}"
 * cvs="cvs {package} {dir} {cvsroot} {module}"
 * url="url {package} {dir}/{fileName} {url}"
""")
    parser.add_argument('packages', nargs='+', help="(Sub-)packages to query")

    parser.add_argument('-D', default=[], action='append', dest="defines",
        help="Override default environment variable")
    parser.add_argument('-c', dest="configFile", default=[], action='append',
        help="Use config File")
    parser.add_argument('-f', default=[], action='append', dest="formats",
        help="Output format for scm (syntax: scm=format). Can be specified multiple times.")
    parser.add_argument('--default', default="", help='Default for missing attributes (default: "")')
    parser.add_argument('-r', '--recursive', default=False, action='store_true',
                        help="Recursively display dependencies")

    formats = {
        'git' : "git {package} {dir} {url} {branch}",
        'svn' : "svn {package} {dir} {url} {revision}",
        'cvs' : "cvs {package} {dir} {cvsroot} {module}",
        'url' : "url {package} {dir}/{fileName} {url}",
    }

    args = parser.parse_args(argv)

    defines = {}
    for define in args.defines:
        d = define.split("=")
        if len(d) == 1:
            defines[d[0]] = ""
        elif len(d) == 2:
            defines[d[0]] = d[1]
        else:
            parser.error("Malformed define: "+define)

    recipes = RecipeSet()
    recipes.setConfigFiles(args.configFile)
    recipes.parse()
    packages = recipes.generatePackages(lambda s,m: "unused", defines)

    # update formats
    for fmt in args.formats:
        f = fmt.split("=")
        if len(f) != 2: parser.error("Malformed format: "+fmt)
        formats[f[0]] = f[1]

    def showPackage(package, recurse, done):
        # show recipes only once for each checkout variant
        key = (package.getRecipe().getName(), package.getCheckoutStep().getVariantId())
        if key not in done:
            for scm in package.getCheckoutStep().getScmList():
                for p in scm.getProperties():
                    p = { k:v for (k,v) in p.items() if v is not None }
                    p['package'] = "/".join(package.getStack())
                    fmt = formats.get(p['scm'], "{scm} {dir}")
                    print(fmt.format_map(Default(args.default, p)))
            done.add(key)

        # recurse package tree if requested
        if recurse:
            for ps in package.getDirectDepSteps():
                showPackage(ps.getPackage(), recurse, done)

    done = set()
    for p in args.packages:
        for package in packages.queryPackagePath(p):
            showPackage(package, args.recursive, done)

def doQueryRecipe(argv, bobRoot):
    parser = argparse.ArgumentParser(prog="bob query-recipe",
        description="Query recipe and class files of package.")
    parser.add_argument('package', help="(Sub-)package to query")
    parser.add_argument('-D', default=[], action='append', dest="defines",
        help="Override default environment variable")
    parser.add_argument('-c', dest="configFile", default=[], action='append',
        help="Use config File")

    args = parser.parse_args(argv)

    defines = {}
    for define in args.defines:
        d = define.split("=")
        if len(d) == 1:
            defines[d[0]] = ""
        elif len(d) == 2:
            defines[d[0]] = d[1]
        else:
            parser.error("Malformed define: "+define)

    recipes = RecipeSet()
    recipes.setConfigFiles(args.configFile)
    recipes.parse()
    package = recipes.generatePackages(lambda s,m: "unused", defines).walkPackagePath(args.package)

    for fn in package.getRecipe().getSources():
        print(fn)
