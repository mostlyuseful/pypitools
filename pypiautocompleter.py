#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import sqlite3
import six

# Ugly hack to be able to redirect output to files
# Since files are considered by the OS to be opaque byte streams, we must manually define a sane encoding.
# See also: http://stackoverflow.com/questions/492483/setting-the-correct-encoding-when-piping-stdout-in-python
if six.PY2:
    if not sys.stdout.isatty():
        import codecs
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)

conn = sqlite3.connect(os.path.expanduser("~/.cache/pypipackagelist.sqlite3"))

c = conn.cursor()

for row in c.execute('SELECT name FROM package ORDER BY name'):
    if six.PY2:
        print(row[0])
    else:
        print(row[0])