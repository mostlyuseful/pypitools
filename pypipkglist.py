#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import argparse
import six
from six import u, print_
if six.PY2:
    import urlparse
else:
    import urllib.parse as urlparse
import requests
from time import time
from sqlalchemy import Column, ForeignKey, Integer, String, Unicode, UnicodeText
from sqlalchemy import create_engine
from sqlalchemy import func, collate
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Ugly hack to be able to redirect output to files
# Since files are considered by the OS to be opaque byte streams, we must manually define a sane encoding.
# See also: http://stackoverflow.com/questions/492483/setting-the-correct-encoding-when-piping-stdout-in-python
if not sys.stdout.isatty():
    import codecs
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)

Base = declarative_base()

class Package(Base):
    __tablename__ = 'package'
    name = Column(Unicode(200), primary_key=True)
    version = Column(Unicode(200))
    description = Column(UnicodeText)
    url = Column(UnicodeText)

    def __str__(self):
        return u("<Package {0}>".format(self.name))
    __repr__=__str__

class Metadata(Base):
    __tablename__ = 'metadata'
    key = Column(Unicode(255), primary_key=True)
    value = Column(UnicodeText)

engine = create_engine("sqlite:///{0}".format(os.path.expanduser("~/.cache/pypipackagelist.sqlite3")))
Base.metadata.create_all(engine)
#Base.metadata.bind = engine

Session = sessionmaker(bind=engine)
session = Session()

def set_metadata(key, value):
    '''
    Sets DB metadata. Both key and value must be (unicode) strings.
    key: Unique key string
    value: Data
    '''
    meta = session.query(Metadata).get(key)
    if meta:
        meta.key=key
        meta.value=value
    else:
        meta = Metadata(key=key, value=value)
    session.add(meta)
    session.commit()

def on_update(args):

    class RepoDecoder(object):
        def __init__(self, repo_url):
            self.repo_url = repo_url
            self.buffer = None
        def feed(self, line):
            # Empty buffer on new table row
            if "<tr" in line:
                self.buffer = []
            elif "</tr>" in line:
                # Table row finished, update package information in DB
                s = u('\n').join(self.buffer)
                # Parse out package information
                m = re.search('<td><a href="(.*?)">(.*?)&nbsp;(.*?)</a></td>.*?<td>(.*?)</td>', s, re.S)
                # Something went wrong, match not found. Abort.
                if not m:
                    return
                pkg_path, pkg_name, pkg_version, pkg_description = m.groups()
                pkg_url = urlparse.urljoin(self.repo_url, pkg_path)
                # Get package, if already in DB
                pkg = session.query(Package).get(pkg_name)
                if pkg:
                    pkg.version = pkg_version
                    pkg.description = pkg_description
                    pkg.url = pkg_url
                else:
                    # Create new package entry
                    pkg = Package(name = pkg_name,
                                version = pkg_version,
                                description = pkg_description,
                                url = pkg_url)
                session.add(pkg)
            else:
                # Inside table row
                self.buffer.append(line)

    repo_url = args.url if args.url else 'http://pypi.python.org/pypi/'
    print_("Connecting to {0}".format(repo_url))
    sys.stdout.flush()
    # Non-blocking request. Use iter_{contents,lines} to collect data
    r = requests.get(repo_url, stream=True)
    # state flag, no simple substring/regex searching possible while streaming
    in_table = False
    # Stateful decoder
    decoder = RepoDecoder(repo_url)
    for i, line in enumerate(r.iter_lines(chunk_size=1024,decode_unicode=True )):
        # Are we in the main table?
        if in_table:
            # Table finished?
            if "</table>" in line:
                # Okay, we're done here
                break
            else:
                # In table, not done -> decode line
                decoder.feed(line)
        else:
            # Wait for beginning of the table
            if "<table" in line:
                in_table = True
        # Status update every 1024*1024 (chunk_size) bytes -> 1kb
        if (i % 1024) == 0:
            print_('.', end='')
            sys.stdout.flush()
    # Not needed right now, but nice to have
    set_metadata(u('last_repo_url'), u(repo_url))
    set_metadata(u('last_update_timestamp'), u(str(time())))
    session.commit()
    print_()
    print_(u('There are {0} packages in the DB.').format(session.query(Package).count()))

def on_list(args):
    if args.simple:
        # List only package names
        fmt = u('{name}')
        max_len_name = None
    else:
        # List package names, its current version and description
        max_len_name = session.query(func.max(func.length(Package.name))).first()[0]
        fmt = u('{name:{max_len_name}}\t{version:10}\t{desc}')

    for pkg in session.query(Package):
        print_(fmt.format(name=pkg.name,
                          version=pkg.version,
                          desc=pkg.description,
                          max_len_name=max_len_name))


def on_search(args):
    # TODO: Decode via actual tty encoding
    try:
        q = args.q[0].decode("utf-8")
    except AttributeError:
        q = args.q[0]
    pkg_names = set()
    # First, check for exact case-insensitive name matches
    for pkg in session.query(Package).filter(collate(Package.name,"NOCASE")==q).all():
        pkg_names.add(pkg.name)
    # Check for substring name matches
    for pkg in session.query(Package).filter(Package.name.like(u('%{0}%').format(q))).all():
        pkg_names.add(pkg.name)
    # Check for description matches
    for pkg in session.query(Package).filter(Package.description.like(u('%{0}%').format(q))).all():
        pkg_names.add(pkg.name)

    if len(pkg_names) == 0:
        print_(u('No matching packages found.'))
        return

    # Nice column formatting
    max_len_name = max( len(name) for name in pkg_names )

    for pkg_name in sorted(pkg_names):
        pkg = session.query(Package).get(pkg_name)
        print_(u('{name:{max_len_name}} {version:10} {desc}'.format(name=pkg.name, version=pkg.version, desc=pkg.description, max_len_name=max_len_name)))


def on_show(args):
    for pkg_name in args.package_names:
        if six.PY2:
            pkg_name = pkg_name.decode("utf-8")
        pkg = session.query(Package).get(pkg_name)
        if pkg:
            print_(u('{name}\t{version}\t{desc}'.format(name=pkg.name, version=pkg.version, desc=pkg.description)))

if __name__=='__main__':
    parser = argparse.ArgumentParser(description="Query a local copy of the PyPI package list")
    subparsers = parser.add_subparsers(dest='subparser_name')
    parser_list = subparsers.add_parser('list')
    parser_list.add_argument('--simple', action='store_true', help='List only package names')
    parser_list.set_defaults(func=on_list)

    parser_update = subparsers.add_parser('update')
    parser_update.add_argument('--url', help='Repository url, default is official PyPI site')
    parser_update.set_defaults(func=on_update)

    parser_search = subparsers.add_parser('search')
    parser_search.add_argument('q', metavar='query', nargs=1)
    parser_search.set_defaults(func=on_search)

    parser_show = subparsers.add_parser('show')
    parser_show.add_argument('package_names', metavar='package', nargs='+')
    parser_show.set_defaults(func=on_show)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        print_(u('No command given. Please run with argument --help'))
